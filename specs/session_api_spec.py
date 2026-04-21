"""BDD Specs for session trace and trigger API endpoints — T027 + T027a.

Covers:
  T027  — /agents/trigger, /sessions/{id}, /agents endpoints
  T027a — tool-call duration_ms completeness, sensitive-field redaction in traces

Uses httpx.AsyncClient with ASGITransport instead of FastAPI's TestClient because
FastAPI 0.109 / Starlette 0.35 bundle an httpx compatibility shim that conflicts
with httpx 0.28's removed ``app=`` keyword on httpx.Client.__init__.
"""
import asyncio
import os
import tempfile

import httpx
from specify import ObjectBehavior

_TMP_SESSIONS = os.path.join(tempfile.gettempdir(), f"api_sessions_{os.getpid()}.db")
_TMP_AUDIT = os.path.join(tempfile.gettempdir(), f"api_audit_{os.getpid()}.db")


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


def _setup_app():
    """Inject temp DBs and a mock agent into src.api.main; return (sm, al)."""
    import src.api.main as m
    from src.sessions.session_manager import SessionManager
    from src.audit.audit_logger import AuditLogger

    sm = SessionManager(db_path=_TMP_SESSIONS)
    al = AuditLogger(db_path=_TMP_AUDIT)
    m._session_manager = sm
    m._audit_logger = al

    class _MockAgent:
        def run(self, session_id, settlement_date):
            sm.update_status(session_id, "completed")
            sm.set_output(
                session_id,
                output={"matched_count": 1, "discrepancy_count": 2, "total_variance_usd": 55.5},
                summary={"matched_count": 1, "discrepancy_count": 2},
            )
            return {"status": "completed"}

    m._agent = _MockAgent()
    return sm, al


class SessionApiSpec(ObjectBehavior):
    """Session trace and agent trigger API endpoints (T027 + T027a)."""

    def _let(self):
        from fastapi import FastAPI
        self._describe(FastAPI)
        self._be_constructed_with(title="FinAgent MVP")

    # ── T027 ──────────────────────────────────────────────────────────────

    def it_triggers_a_reconciliation_session(self):
        """POST /agents/trigger returns 200 with a session_id."""
        _setup_app()
        resp = _req(
            "post",
            "/agents/trigger",
            json={
                "agent_name": "settlement-reconciliation-agent",
                "params": {"settlement_date": "2026-04-20"},
            },
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "session_id" in data, f"Missing session_id in {data}"

    def it_returns_404_for_unknown_session(self):
        """GET /sessions/{id} returns 404 when session does not exist."""
        _setup_app()
        resp = _req("get", "/sessions/no-such-session-00000")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    def it_returns_session_trace_for_known_session(self):
        """GET /sessions/{id} returns 200 with session_id, tool_calls, audit_events."""
        _setup_app()
        trigger = _req(
            "post",
            "/agents/trigger",
            json={
                "agent_name": "settlement-reconciliation-agent",
                "params": {"settlement_date": "2026-04-20"},
            },
        )
        session_id = trigger.json()["session_id"]

        resp = _req("get", f"/sessions/{session_id}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["session_id"] == session_id
        assert "tool_calls" in data
        assert "audit_events" in data
        assert "status" in data

    def it_lists_registered_agents(self):
        """GET /agents returns a non-empty list with agent metadata."""
        _setup_app()
        resp = _req("get", "/agents")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert "agents" in data, f"Missing 'agents' key in {data}"
        assert len(data["agents"]) >= 1, f"Expected at least one agent, got {data}"
        agent = data["agents"][0]
        assert "name" in agent, f"Agent missing 'name': {agent}"

    # ── T027a ─────────────────────────────────────────────────────────────

    def it_captures_duration_ms_in_tool_calls(self):
        """T027a: tool calls in the trace must carry a duration_ms value."""
        sm, al = _setup_app()
        trigger = _req(
            "post",
            "/agents/trigger",
            json={
                "agent_name": "settlement-reconciliation-agent",
                "params": {"settlement_date": "2026-04-20"},
            },
        )
        session_id = trigger.json()["session_id"]

        sm.add_tool_call(
            session_id,
            {
                "tool_name": "reconcile.run",
                "duration_ms": 42,
                "timestamp": "2026-04-20T10:00:00",
                "input": {"record_count": 3},
                "output": {"matched": 1, "discrepancies": 2},
            },
        )

        resp = _req("get", f"/sessions/{session_id}")
        data = resp.json()
        reconcile_calls = [tc for tc in data["tool_calls"] if tc.get("tool_name") == "reconcile.run"]
        assert len(reconcile_calls) >= 1, f"Expected reconcile.run call, got {data['tool_calls']}"
        assert reconcile_calls[0]["duration_ms"] == 42, (
            f"Expected duration_ms=42, got {reconcile_calls[0]}"
        )

    def it_redacts_sensitive_fields_in_trace(self):
        """T027a: sensitive fields (password, token…) are redacted in the trace response."""
        sm, al = _setup_app()
        trigger = _req(
            "post",
            "/agents/trigger",
            json={
                "agent_name": "settlement-reconciliation-agent",
                "params": {"settlement_date": "2026-04-20"},
            },
        )
        session_id = trigger.json()["session_id"]

        sm.add_tool_call(
            session_id,
            {
                "tool_name": "postgres.query",
                "duration_ms": 15,
                "timestamp": "2026-04-20T10:00:01",
                "input": {"sql": "SELECT *", "password": "hunter2"},
                "output": {"rows": 3},
            },
        )

        resp = _req("get", f"/sessions/{session_id}")
        data = resp.json()
        pg_calls = [tc for tc in data["tool_calls"] if tc.get("tool_name") == "postgres.query"]
        assert len(pg_calls) >= 1, f"Expected postgres.query call in {data['tool_calls']}"
        tc_input = pg_calls[0]["input"]
        assert tc_input["password"] == "***REDACTED***", f"Expected redaction: {tc_input}"
        assert tc_input["sql"] == "SELECT *", f"Non-sensitive field must not be redacted: {tc_input}"
