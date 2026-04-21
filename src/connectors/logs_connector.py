"""Logs connector for FinAgent — searches structured log files for payout evidence."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .base import Connector, ConnectorResult


class LogsConnector(Connector):
    """Reads a newline-delimited log file and returns lines matching a payout_id."""

    @property
    def connector_type(self) -> str:
        return "logs"

    def _read_log(self) -> str:
        """Read the log file as a single string. Separated for easy mocking."""
        log_path = self.config.get("log_path", "")
        path = Path(log_path)
        if not path.exists():
            raise FileNotFoundError(f"Log file not found: {path}")
        return path.read_text(encoding="utf-8")

    async def query(self, request: dict[str, Any]) -> ConnectorResult:
        """
        Search log lines for a specific payout_id.

        Request keys:
          payout_id (str): The payout identifier to search for.
          max_lines (int): Maximum number of matching lines to return (default 50).
        """
        payout_id = request.get("payout_id")
        if not payout_id:
            return ConnectorResult(
                success=False,
                error="Request must include 'payout_id' key",
                connector_name=self.name,
            )

        max_lines: int = request.get("max_lines", 50)
        start = time.monotonic()
        try:
            content = self._read_log()
        except Exception as exc:
            return ConnectorResult(
                success=False,
                error=str(exc),
                connector_name=self.name,
            )

        matches = []
        for line in content.splitlines():
            if payout_id in line:
                matches.append({"line": line})
                if len(matches) >= max_lines:
                    break

        elapsed = int((time.monotonic() - start) * 1000)
        return ConnectorResult(
            success=True,
            data=matches,
            execution_time_ms=elapsed,
            connector_name=self.name,
        )

    async def health_check(self) -> bool:
        log_path = self.config.get("log_path", "")
        return Path(log_path).exists()
