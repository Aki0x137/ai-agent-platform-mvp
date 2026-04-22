"""Approval gate handling for paused reconciliation sessions."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from src.audit.audit_logger import AuditLogger
from src.core.langgraph_agent import ReconciliationAgent
from src.sessions.session_manager import SessionManager


class ApprovalService:
    """Apply human approval decisions to paused sessions."""

    def __init__(
        self,
        session_manager: SessionManager,
        audit_logger: AuditLogger,
        agent: ReconciliationAgent,
    ) -> None:
        self.sm = session_manager
        self.al = audit_logger
        self.agent = agent

    async def decide(
        self,
        session_id: str,
        approved_by: Optional[str],
        comment: Optional[str],
        status: str,
    ) -> Dict[str, Any]:
        """Approve or reject a paused session.

        Returns a dict with ``gate_status`` and ``next_status`` suitable for the
        approval endpoint response.
        """
        session = self.sm.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id!r} not found")
        if session.get("status") != "paused":
            raise RuntimeError(f"Session {session_id!r} is not paused")

        gate_payload = {
            "gate_name": "create_investigation_ticket",
            "status": status,
            "approved_by": approved_by,
            "comment": comment,
        }
        self.al.log(session_id, "human_gate", gate_payload)

        if status == "approved":
            try:
                ticket_reference = await self.agent.create_ticket_after_approval(session_id)
                resumed = self.agent.resume_after_approval(
                    session_id,
                    approved_by,
                    comment,
                    ticket_reference=ticket_reference,
                )
            except Exception as exc:  # noqa: BLE001
                failed = self.agent.mark_ticket_creation_failed(
                    session_id,
                    str(exc),
                    approved_by=approved_by,
                    comment=comment,
                )
                return {
                    "session_id": session_id,
                    "gate_status": "approved",
                    "next_status": failed.get("status", "failed"),
                    "message": "Approval accepted, but ticket creation failed.",
                    "error": str(exc),
                }
            return {
                "session_id": session_id,
                "gate_status": "approved",
                "next_status": resumed.get("status", "completed"),
                "ticket_reference": ticket_reference,
                "message": "Approval accepted; session resumed.",
            }

        return {
            "session_id": session_id,
            "gate_status": "rejected",
            "next_status": session.get("status", "paused"),
            "message": "Approval rejected; session remains paused.",
        }