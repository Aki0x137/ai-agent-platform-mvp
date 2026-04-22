"""Stub-backed MCP connector for investigation ticket creation."""
from __future__ import annotations

from rich.console import Console
console = Console()

import json
import os
import time
from typing import Any

from .base import Connector, ConnectorResult


class MCPConnector(Connector):
    """Loads deterministic ticket creation results from local stub files."""

    @property
    def connector_type(self) -> str:
        return "mcp"

    def _stub_dir(self) -> str:
        return self.config.get("stub_dir", "docker/mcp_stub")

    def _fixture_path(self, simulate_failure: bool) -> str:
        filename = "failure_ticket.json" if simulate_failure else "success_ticket.json"
        return os.path.join(self._stub_dir(), filename)

    def _load_stub(self, simulate_failure: bool) -> dict[str, Any]:
        with open(self._fixture_path(simulate_failure), "r", encoding="utf-8") as fh:
            return json.load(fh)

    async def query(self, request: dict[str, Any]) -> ConnectorResult:
        """Create a ticket using local stub artifacts.

        Request keys:
          action (str): must be ``create_ticket``.
          simulate_failure (bool): if true, return the failure stub.
          summary/evidence/session_id: optional metadata for callers.
        """
        console.print(f"[bold blue]🔌 Connector ({self.name}):[/bold blue] Processing MCP action '[yellow]{request.get('action')}[/yellow]'")
        action = request.get("action")
        if not action:
            return ConnectorResult(
                success=False,
                error="Request must include 'action' key",
                connector_name=self.name,
            )
        if action != "create_ticket":
            return ConnectorResult(
                success=False,
                error=f"Unsupported MCP action: {action}",
                connector_name=self.name,
            )

        simulate_failure = bool(request.get("simulate_failure", self.config.get("simulate_failure", False)))
        start = time.monotonic()
        try:
            payload = self._load_stub(simulate_failure)
            elapsed = int((time.monotonic() - start) * 1000)
            if simulate_failure:
                return ConnectorResult(
                    success=False,
                    error=payload.get("error", "MCP ticket creation failed"),
                    execution_time_ms=elapsed,
                    connector_name=self.name,
                )

            result = {
                **payload,
                "session_id": request.get("session_id"),
                "summary": request.get("summary") or payload.get("summary"),
                "evidence": request.get("evidence", {}),
            }
            return ConnectorResult(
                success=True,
                data=[result],
                execution_time_ms=elapsed,
                connector_name=self.name,
            )
        except Exception as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            return ConnectorResult(
                success=False,
                error=str(exc),
                execution_time_ms=elapsed,
                connector_name=self.name,
            )