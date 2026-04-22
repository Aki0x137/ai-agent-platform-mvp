"""BDD Specs for approval-gate API endpoints — T034."""
import asyncio
import os
import tempfile

import httpx
from specify import ObjectBehavior

_TMP_SESSIONS = os.path.join(tempfile.gettempdir(), f"approval_api_sessions_{os.getpid()}.db")
_TMP_AUDIT = os.path.join(tempfile.gettempdir(), f"approval_api_audit_{os.getpid()}.db")


def _req(method: str, path: str, **kwargs):
    """Make a synchronous HTTP call to the FastAPI app via ASGITransport."""
    from src.api.main import app

    async def _inner():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            return await getattr(client, method)(path, **kwargs)

    return asyncio.get_event_loop().run_until_complete(_inner())


def _setup_real_app():
    """Inject temp DBs and reset the real reconciliation + approval services."""
    import src.api.main as m
    from src.sessions.session_manager import SessionManager
    from src.audit.audit_logger import AuditLogger

    sm = SessionManager(db_path=_TMP_SESSIONS)
    al = AuditLogger(db_path=_TMP_AUDIT)
    m._session_manager = sm
    m._audit_logger = al
    m._agent = None
    m._approval_service = None
    return sm, al


def _setup_completed_app():
    """Inject temp DBs and a mock agent that completes immediately."""
    import src.api.main as m
    from src.sessions.session_manager import SessionManager
    from src.audit.audit_logger import AuditLogger

    sm = SessionManager(db_path=_TMP_SESSIONS)
    al = AuditLogger(db_path=_TMP_AUDIT)
    m._session_manager = sm
    m._audit_logger = al
    m._approval_service = None

    class _MockAgent:
        def run(self, session_id, settlement_date):
            sm.update_status(session_id, "completed")
            sm.set_output(
                session_id,
                output={"matched_count": 1, "discrepancy_count": 0, "total_variance_usd": 0.0},
                summary={"matched_count": 1, "discrepancy_count": 0},
            )
            return {"status": "completed", "needs_approval": False}

    m._agent = _MockAgent()
    return sm, al


class ApprovalApiSpec(ObjectBehavior):
    """Approval gate API resumes paused sessions across the approval boundary."""

    def _let(self):
        from fastapi import FastAPI
        self._describe(FastAPI)
        self._be_constructed_with(title="FinAgent MVP")

    def it_approves_a_paused_session_and_resumes_to_completed(self):
        """POST /sessions/{id}/approve completes a paused session when approved."""
        _setup_real_app()
        trigger = _req(
            "post",
            "/agents/trigger",
            json={
                "agent_name": "settlement-reconciliation-agent",
                "params": {"settlement_date": "2026-04-20"},
            },
        )
        session_id = trigger.json()["session_id"]

        resp = _req(
            "post",
            f"/sessions/{session_id}/approve",
            json={"approved_by": "analyst@finagent.local", "comment": "Proceed", "status": "approved"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["gate_status"] == "approved", f"Expected approved gate_status, got {data}"
        assert data["next_status"] == "completed", f"Expected completed next_status, got {data}"

        session = _req("get", f"/sessions/{session_id}").json()
        assert session["status"] == "completed", f"Expected completed session, got {session}"
        statuses = [e["payload"].get("status") for e in session["audit_events"] if e["event_type"] == "human_gate"]
        assert "approved" in statuses, f"Expected approved human_gate audit event, got {session['audit_events']}"

    def it_keeps_a_session_paused_when_rejected(self):
        """POST /sessions/{id}/approve with status=rejected leaves the session paused."""
        _setup_real_app()
        trigger = _req(
            "post",
            "/agents/trigger",
            json={
                "agent_name": "settlement-reconciliation-agent",
                "params": {"settlement_date": "2026-04-20"},
            },
        )
        session_id = trigger.json()["session_id"]

        resp = _req(
            "post",
            f"/sessions/{session_id}/approve",
            json={"approved_by": "analyst@finagent.local", "comment": "Do not proceed", "status": "rejected"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["gate_status"] == "rejected", f"Expected rejected gate_status, got {data}"
        assert data["next_status"] == "paused", f"Expected paused next_status, got {data}"

        session = _req("get", f"/sessions/{session_id}").json()
        assert session["status"] == "paused", f"Expected paused session, got {session}"

    def it_returns_404_for_unknown_session_on_approve(self):
        """POST /sessions/{id}/approve returns 404 when the session does not exist."""
        _setup_real_app()
        resp = _req(
            "post",
            "/sessions/no-such-session-00000/approve",
            json={"approved_by": "analyst@finagent.local", "comment": "Proceed", "status": "approved"},
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"

    def it_returns_409_when_session_is_not_paused(self):
        """POST /sessions/{id}/approve returns 409 if the session is already completed."""
        _setup_completed_app()
        trigger = _req(
            "post",
            "/agents/trigger",
            json={
                "agent_name": "settlement-reconciliation-agent",
                "params": {"settlement_date": "2026-04-20"},
            },
        )
        session_id = trigger.json()["session_id"]

        resp = _req(
            "post",
            f"/sessions/{session_id}/approve",
            json={"approved_by": "analyst@finagent.local", "comment": "Proceed", "status": "approved"},
        )
        assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text}"