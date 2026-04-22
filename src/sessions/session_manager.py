"""SQLite-backed session manager for FinAgent MVP.

Each session stores:
- identity  (id, agent_id, created_at, updated_at)
- lifecycle  (status, error_message)
- payload   (input_params, output_result, summary)
- trace     (tool_calls — a JSON array appended to on each tool execution)

The design mirrors the Mem0 session-storage contract so the backend can be
swapped in production without changing the calling interface.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id                  TEXT PRIMARY KEY,
    agent_id            TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'pending',
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    input_params_json   TEXT NOT NULL DEFAULT '{}',
    output_result_json  TEXT,
    tool_calls_json     TEXT NOT NULL DEFAULT '[]',
    error_message       TEXT,
    summary_json        TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_agent ON sessions (agent_id);
"""


class SessionManager:
    """Lightweight SQLite-backed session manager.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file.  The parent directory is created
        automatically.
    """

    def __init__(self, db_path: str = "data/sessions.db") -> None:
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

    @staticmethod
    def _row_to_dict(row: tuple) -> Dict[str, Any]:
        return {
            "id": row[0],
            "agent_id": row[1],
            "status": row[2],
            "created_at": row[3],
            "updated_at": row[4],
            "input_params": json.loads(row[5]),
            "output_result": json.loads(row[6]) if row[6] else None,
            "tool_calls": json.loads(row[7]),
            "error_message": row[8],
            "summary": json.loads(row[9]) if row[9] else None,
        }

    # ── Public API ───────────────────────────────────────────────────────

    def create_session(
        self,
        agent_id: str,
        input_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new session with status=pending; return its dict."""
        session_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        params = input_params or {}
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sessions "
                "(id, agent_id, status, created_at, updated_at, input_params_json, tool_calls_json) "
                "VALUES (?, ?, 'pending', ?, ?, ?, '[]')",
                (session_id, agent_id, now, now, json.dumps(params)),
            )
            conn.commit()
        return self.get_session(session_id)  # type: ignore[return-value]

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Return the full session dict, or None if not found."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, agent_id, status, created_at, updated_at, "
                "input_params_json, output_result_json, tool_calls_json, "
                "error_message, summary_json "
                "FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def update_status(
        self,
        session_id: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update status (and optional error) on a session; return updated dict."""
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions SET status = ?, updated_at = ?, error_message = ? WHERE id = ?",
                (status, now, error_message, session_id),
            )
            conn.commit()
        return self.get_session(session_id)  # type: ignore[return-value]

    def add_tool_call(self, session_id: str, tool_call: Dict[str, Any]) -> None:
        """Append *tool_call* to the session's tool_calls JSON array."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT tool_calls_json FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if row is None:
                return
            calls: list = json.loads(row[0])
            calls.append(tool_call)
            now = datetime.utcnow().isoformat()
            conn.execute(
                "UPDATE sessions SET tool_calls_json = ?, updated_at = ? WHERE id = ?",
                (json.dumps(calls), now, session_id),
            )
            conn.commit()

    def set_output(
        self,
        session_id: str,
        output: Dict[str, Any],
        summary: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persist the final output and summary on the session."""
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions "
                "SET output_result_json = ?, summary_json = ?, updated_at = ? "
                "WHERE id = ?",
                (
                    json.dumps(output),
                    json.dumps(summary) if summary is not None else None,
                    now,
                    session_id,
                ),
            )
            conn.commit()

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Return summary rows for all sessions, most-recent first."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, agent_id, status, created_at, updated_at "
                "FROM sessions ORDER BY created_at DESC"
            ).fetchall()
        return [
            {
                "id": r[0],
                "agent_id": r[1],
                "status": r[2],
                "created_at": r[3],
                "updated_at": r[4],
            }
            for r in rows
        ]
