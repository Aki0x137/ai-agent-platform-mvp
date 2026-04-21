"""Payload shaping and sensitive-field redaction for session trace API — T032 + T032a.

``shape_trace`` converts raw session + audit-event data into the
``GET /sessions/{id}`` response body.

``redact_payload`` recursively replaces values whose key is sensitive
(password, token, secret, key, auth, credential, passwd, pwd) with
``***REDACTED***``.  Key detection uses the same word-segment strategy
as ``src/router/__init__.py`` so the two redaction passes stay in sync.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

_SENSITIVE_SEGMENTS: frozenset[str] = frozenset(
    {"password", "token", "secret", "credential", "key", "auth", "passwd", "pwd"}
)


def _is_sensitive_key(key: str) -> bool:
    key_lower = key.lower()
    if key_lower in _SENSITIVE_SEGMENTS:
        return True
    segments = set(re.split(r"[_\-\s]", key_lower)) - {""}
    return bool(segments & _SENSITIVE_SEGMENTS)


def redact_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of *payload* with sensitive values replaced."""
    result: Dict[str, Any] = {}
    for k, v in payload.items():
        if _is_sensitive_key(k):
            result[k] = "***REDACTED***"
        elif isinstance(v, dict):
            result[k] = redact_payload(v)
        else:
            result[k] = v
    return result


def shape_trace(
    session: Dict[str, Any],
    audit_events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Shape raw session + audit data into the API trace response body.

    - Redacts sensitive fields in every tool-call input/output.
    - Preserves ``duration_ms`` and all routing metadata.
    - Adds ``agent_name`` with a sensible default when absent.
    """
    redacted_tool_calls: List[Dict[str, Any]] = []
    for tc in session.get("tool_calls", []):
        shaped = dict(tc)
        if "input" in shaped and isinstance(shaped["input"], dict):
            shaped["input"] = redact_payload(shaped["input"])
        if "output" in shaped and isinstance(shaped["output"], dict):
            shaped["output"] = redact_payload(shaped["output"])
        redacted_tool_calls.append(shaped)

    return {
        "session_id": session["id"],
        "agent_id": session["agent_id"],
        "agent_name": session.get("agent_name", "settlement-reconciliation-agent"),
        "status": session["status"],
        "created_at": session["created_at"],
        "updated_at": session["updated_at"],
        "tool_calls": redacted_tool_calls,
        "audit_events": audit_events,
        "output": session.get("output_result"),
        "summary": session.get("summary"),
    }
