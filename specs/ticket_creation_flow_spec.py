"""BDD Specs for end-to-end ticket creation flow — T035 + T035a."""
import asyncio
import os
import tempfile

import httpx
from specify import ObjectBehavior

_TMP_SESSIONS = os.path.join(tempfile.gettempdir(), f"ticket_flow_sessions_{os.getpid()}.db")
_TMP_AUDIT = os.path.join(tempfile.gettempdir(), f"ticket_flow_audit_{os.getpid()}.db")


def _req(method: str, path: str, **kwargs):
    """Make a synchronous HTTP call to the FastAPI app via ASGITransport."""
    from src.api.main import app

    async def _inner():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await getattr(client, method)(path, **kwargs)

    return asyncio.get_event_loop().run_until_complete(_inner())


def _setup_app(simulate_failure: bool = False):
    """Inject temp stores and a real agent configured for success or failure."""
    import src.api.main as m
    from src.audit.audit_logger import AuditLogger
    from src.core.approval_service import ApprovalService
    from src.core.langgraph_agent import ReconciliationAgent
    from src.sessions.session_manager import SessionManager

    sm = SessionManager(db_path=_TMP_SESSIONS)
    al = AuditLogger(db_path=_TMP_AUDIT)
    agent = ReconciliationAgent(
        session_manager=sm,
        audit_logger=al,
        mcp_connector_config={
            "stub_dir": "docker/mcp_stub",
            "simulate_failure": simulate_failure,
        },
    )

    m._session_manager = sm
    m._audit_logger = al
    m._agent = agent
    m._approval_service = ApprovalService(
        session_manager=sm,
        audit_logger=al,
        agent=agent,
    )
    return sm, al


class TicketCreationFlowSpec(ObjectBehavior):
    """Approval should create a ticket artifact and persist it on the session."""

    def _let(self):
        from fastapi import FastAPI
        self._describe(FastAPI)
        self._be_constructed_with(title="FinAgent MVP")

    def it_creates_a_ticket_after_approval(self):
        """Approving a paused session creates a ticket artifact and completes the session."""
        _setup_app(simulate_failure=False)
        trigger = _req(
            "post",
            "/agents/trigger",
            json={
                "agent_name": "settlement-reconciliation-agent",
                "params": {"settlement_date": "2026-04-20"},
            },
        )
        session_id = trigger.json()["session_id"]

        approve = _req(
            "post",
            f"/sessions/{session_id}/approve",
            json={"approved_by": "demo-user", "comment": "Proceed", "status": "approved"},
        )
        assert approve.status_code == 200, f"Expected 200, got {approve.status_code}: {approve.text}"
        data = approve.json()
        assert data["next_status"] == "completed", f"Expected completed status, got {data}"
        assert data["ticket_reference"]["ticket_id"].startswith("INV-"), f"Expected ticket reference, got {data}"

        session = _req("get", f"/sessions/{session_id}").json()
        assert session["status"] == "completed", f"Expected completed session, got {session}"
        ticket_reference = session["output"]["ticket_reference"]
        assert ticket_reference["ticket_id"].startswith("INV-"), f"Expected persisted ticket reference, got {session}"

    def it_records_ticket_creation_failure_auditably(self):
        """A stubbed MCP failure marks the session failed and preserves the error in trace/output."""
        _setup_app(simulate_failure=True)
        trigger = _req(
            "post",
            "/agents/trigger",
            json={
                "agent_name": "settlement-reconciliation-agent",
                "params": {"settlement_date": "2026-04-20"},
            },
        )
        session_id = trigger.json()["session_id"]

        approve = _req(
            "post",
            f"/sessions/{session_id}/approve",
            json={"approved_by": "demo-user", "comment": "Proceed", "status": "approved"},
        )
        assert approve.status_code == 200, f"Expected 200, got {approve.status_code}: {approve.text}"
        data = approve.json()
        assert data["next_status"] == "failed", f"Expected failed status, got {data}"
        assert "error" in data, f"Expected error details, got {data}"

        session = _req("get", f"/sessions/{session_id}").json()
        assert session["status"] == "failed", f"Expected failed session, got {session}"
        assert session["output"]["ticket_error"], f"Expected ticket error in output, got {session}"
        errors = [e for e in session["audit_events"] if e["event_type"] == "error"]
        assert len(errors) >= 1, f"Expected at least one error audit event, got {session['audit_events']}"