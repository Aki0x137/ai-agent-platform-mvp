"""BDD Specs for AuditLogger — T025.

AuditLogger writes immutable, SHA-256-hashed audit events to SQLite
and redacts sensitive keys from every payload before storage.
"""
import os
import tempfile

from specify import ObjectBehavior

from src.audit.audit_logger import AuditLogger

# One shared temp DB per process; tests use distinct session IDs so they
# do not interfere with each other even though the file is shared.
_TMP_DB = os.path.join(tempfile.gettempdir(), f"audit_spec_{os.getpid()}.db")


class AuditLoggerSpec(ObjectBehavior):
    """AuditLogger writes immutable, integrity-hashed audit events."""

    def _let(self):
        self._describe(AuditLogger)
        self._be_constructed_with(db_path=_TMP_DB)

    def it_logs_a_tool_call_event(self):
        """log() returns a dict with event_type, session_id, and immutable_hash."""
        al = AuditLogger(db_path=_TMP_DB)
        event = al.log("sess-al-01", "tool_call", {"tool": "postgres.query", "result": "ok"})
        assert event["event_type"] == "tool_call", f"got {event['event_type']}"
        assert event["session_id"] == "sess-al-01"
        assert "immutable_hash" in event, "missing immutable_hash"
        assert len(event["immutable_hash"]) == 64, "hash should be 64 hex chars (SHA-256)"

    def it_retrieves_events_by_session_id(self):
        """get_events() returns all events logged for a session in timestamp order."""
        al = AuditLogger(db_path=_TMP_DB)
        al.log("sess-al-02", "tool_call", {"tool": "postgres.query"})
        al.log("sess-al-02", "checkpoint", {"step": "reconcile"})
        events = al.get_events("sess-al-02")
        assert len(events) == 2, f"Expected 2 events, got {len(events)}"
        types = [e["event_type"] for e in events]
        assert "tool_call" in types
        assert "checkpoint" in types

    def it_redacts_sensitive_fields(self):
        """Sensitive keys (password, token, secret…) are replaced with ***REDACTED***."""
        al = AuditLogger(db_path=_TMP_DB)
        event = al.log(
            "sess-al-03",
            "tool_call",
            {"password": "hunter2", "tool": "db.query", "auth_token": "abc123"},
        )
        assert event["payload"]["password"] == "***REDACTED***", event["payload"]
        assert event["payload"]["auth_token"] == "***REDACTED***", event["payload"]
        assert event["payload"]["tool"] == "db.query"

    def it_verifies_event_integrity(self):
        """verify_integrity() returns True for an unmodified event."""
        al = AuditLogger(db_path=_TMP_DB)
        event = al.log("sess-al-04", "checkpoint", {"step": "done"})
        assert al.verify_integrity(event), "Integrity check should pass for untouched event"

    def it_detects_tampered_events(self):
        """verify_integrity() returns False when payload has been altered."""
        al = AuditLogger(db_path=_TMP_DB)
        event = al.log("sess-al-05", "checkpoint", {"step": "done"})
        tampered = dict(event)
        tampered["payload"] = {"step": "hacked"}
        assert not al.verify_integrity(tampered), "Tampered event must fail integrity check"

    def it_does_not_return_events_for_other_sessions(self):
        """get_events() returns only events belonging to the requested session_id."""
        al = AuditLogger(db_path=_TMP_DB)
        al.log("sess-al-06", "tool_call", {"tool": "logs.search"})
        events = al.get_events("sess-al-UNKNOWN")
        assert len(events) == 0, f"Expected 0 events for unknown session, got {len(events)}"
