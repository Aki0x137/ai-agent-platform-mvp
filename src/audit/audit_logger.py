"""Immutable, integrity-hashed audit logger backed by SQLite.

Every event is:
- redacted (sensitive keys replaced with ***REDACTED***)
- hashed with SHA-256 (id + session_id + event_type + timestamp + payload_json)
- written once and never updated (append-only table)

Sensitive key detection reuses the same word-segment strategy as the payload
classifier in src/router/__init__.py.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List

_SENSITIVE_SEGMENTS: frozenset[str] = frozenset(
    {"password", "token", "secret", "credential", "key", "auth", "passwd", "pwd"}
)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS audit_events (
    id            TEXT PRIMARY KEY,
    session_id    TEXT NOT NULL,
    event_type    TEXT NOT NULL,
    timestamp     TEXT NOT NULL,
    payload_json  TEXT NOT NULL,
    immutable_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_events (session_id);
"""


def _is_sensitive_key(key: str) -> bool:
    """Return True if *key* contains a sensitive word segment."""
    key_lower = key.lower()
    if key_lower in _SENSITIVE_SEGMENTS:
        return True
    segments = set(re.split(r"[_\-\s]", key_lower)) - {""}
    return bool(segments & _SENSITIVE_SEGMENTS)


class AuditLogger:
    """Append-only SQLite audit logger.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file.  The parent directory is created
        automatically.  Pass ``":memory:"`` only for ephemeral testing via a
        persistent shared connection (see ``_conn`` arg).
    """

    def __init__(self, db_path: str = "data/audit.db") -> None:
        self.db_path = db_path
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._ensure_table()

    # ── Private ─────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _ensure_table(self) -> None:
        with self._connect() as conn:
            conn.executescript(_CREATE_TABLE_SQL)
            conn.commit()

    def _redact(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact values whose key is deemed sensitive."""
        result: Dict[str, Any] = {}
        for k, v in payload.items():
            if _is_sensitive_key(k):
                result[k] = "***REDACTED***"
            elif isinstance(v, dict):
                result[k] = self._redact(v)
            else:
                result[k] = v
        return result

    @staticmethod
    def _compute_hash(
        event_id: str,
        session_id: str,
        event_type: str,
        timestamp: str,
        payload_json: str,
    ) -> str:
        raw = f"{event_id}:{session_id}:{event_type}:{timestamp}:{payload_json}"
        return hashlib.sha256(raw.encode()).hexdigest()

    # ── Public API ───────────────────────────────────────────────────────

    def log(
        self,
        session_id: str,
        event_type: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Write one immutable audit event; returns the persisted event dict."""
        redacted = self._redact(payload)
        event_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        payload_json = json.dumps(redacted, sort_keys=True, default=str)
        immutable_hash = self._compute_hash(
            event_id, session_id, event_type, timestamp, payload_json
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?)",
                (event_id, session_id, event_type, timestamp, payload_json, immutable_hash),
            )
            conn.commit()
        return {
            "id": event_id,
            "session_id": session_id,
            "event_type": event_type,
            "timestamp": timestamp,
            "payload": redacted,
            "immutable_hash": immutable_hash,
        }

    def get_events(self, session_id: str) -> List[Dict[str, Any]]:
        """Return all audit events for *session_id*, ordered by timestamp."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, session_id, event_type, timestamp, payload_json, immutable_hash "
                "FROM audit_events WHERE session_id = ? ORDER BY timestamp",
                (session_id,),
            ).fetchall()
        return [
            {
                "id": r[0],
                "session_id": r[1],
                "event_type": r[2],
                "timestamp": r[3],
                "payload": json.loads(r[4]),
                "immutable_hash": r[5],
            }
            for r in rows
        ]

    def verify_integrity(self, event: Dict[str, Any]) -> bool:
        """Return True if *event*'s hash matches its content (tamper detection)."""
        payload_json = json.dumps(event["payload"], sort_keys=True, default=str)
        expected = self._compute_hash(
            event["id"],
            event["session_id"],
            event["event_type"],
            event["timestamp"],
            payload_json,
        )
        return event["immutable_hash"] == expected
