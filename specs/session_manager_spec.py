"""BDD Specs for SessionManager — T026.

SessionManager creates and persists reconciliation sessions using SQLite
and provides status updates, tool-call append, and output storage.
"""
import os
import tempfile

from specify import ObjectBehavior

from src.sessions.session_manager import SessionManager

_TMP_DB = os.path.join(tempfile.gettempdir(), f"sessions_spec_{os.getpid()}.db")


class SessionManagerSpec(ObjectBehavior):
    """SessionManager tracks session lifecycle and tool-call history."""

    def _let(self):
        self._describe(SessionManager)
        self._be_constructed_with(db_path=_TMP_DB)

    def it_creates_a_session_with_pending_status(self):
        """create_session() returns a session dict with status='pending'."""
        sm = SessionManager(db_path=_TMP_DB)
        session = sm.create_session("agent-001", {"settlement_date": "2026-04-20"})
        assert session["status"] == "pending", f"got {session['status']}"
        assert session["agent_id"] == "agent-001"
        assert session["input_params"]["settlement_date"] == "2026-04-20"
        assert "id" in session

    def it_retrieves_a_session_by_id(self):
        """get_session() returns the session created by create_session()."""
        sm = SessionManager(db_path=_TMP_DB)
        created = sm.create_session("agent-001", {})
        retrieved = sm.get_session(created["id"])
        assert retrieved is not None, "Expected session to be retrievable"
        assert retrieved["id"] == created["id"]

    def it_returns_none_for_unknown_session(self):
        """get_session() returns None when session_id does not exist."""
        sm = SessionManager(db_path=_TMP_DB)
        result = sm.get_session("nonexistent-id-9999")
        assert result is None, f"Expected None, got {result}"

    def it_updates_session_status(self):
        """update_status() transitions session to the requested status."""
        sm = SessionManager(db_path=_TMP_DB)
        session = sm.create_session("agent-001", {})
        updated = sm.update_status(session["id"], "running")
        assert updated["status"] == "running", f"got {updated['status']}"

    def it_appends_tool_calls(self):
        """add_tool_call() appends a tool-call record to the session."""
        sm = SessionManager(db_path=_TMP_DB)
        session = sm.create_session("agent-001", {})
        sm.add_tool_call(session["id"], {"tool_name": "postgres.query", "duration_ms": 120})
        retrieved = sm.get_session(session["id"])
        assert len(retrieved["tool_calls"]) == 1, f"got {retrieved['tool_calls']}"
        assert retrieved["tool_calls"][0]["tool_name"] == "postgres.query"

    def it_accumulates_multiple_tool_calls(self):
        """add_tool_call() called twice yields two records in order."""
        sm = SessionManager(db_path=_TMP_DB)
        session = sm.create_session("agent-001", {})
        sm.add_tool_call(session["id"], {"tool_name": "load_data", "duration_ms": 5})
        sm.add_tool_call(session["id"], {"tool_name": "reconcile.run", "duration_ms": 50})
        retrieved = sm.get_session(session["id"])
        names = [tc["tool_name"] for tc in retrieved["tool_calls"]]
        assert names == ["load_data", "reconcile.run"], f"got {names}"

    def it_sets_output_and_summary(self):
        """set_output() persists the result and summary on the session."""
        sm = SessionManager(db_path=_TMP_DB)
        session = sm.create_session("agent-001", {})
        sm.set_output(
            session["id"],
            output={"matched_count": 1, "discrepancy_count": 2},
            summary={"matched": 1, "discrepancies": 2},
        )
        retrieved = sm.get_session(session["id"])
        assert retrieved["output_result"]["matched_count"] == 1
        assert retrieved["summary"]["matched"] == 1

    def it_lists_all_sessions(self):
        """list_sessions() returns summary rows for all sessions."""
        sm = SessionManager(db_path=_TMP_DB)
        sm.create_session("agent-002", {})
        sm.create_session("agent-002", {})
        sessions = sm.list_sessions()
        # At least the 2 just created (may be more from other tests in this run)
        assert len(sessions) >= 2, f"Expected >= 2 sessions, got {len(sessions)}"
        assert all("id" in s and "status" in s for s in sessions)
