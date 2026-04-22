"""REST API connector for FinAgent."""
from __future__ import annotations

import time
from typing import Any

from .base import Connector, ConnectorResult


class RestApiConnector(Connector):
    """Fetches data from HTTP REST endpoints using httpx."""

    @property
    def connector_type(self) -> str:
        return "rest_api"

    def _base_url(self) -> str:
        return self.config.get("base_url", "").rstrip("/")

    async def _get(self, url: str, params: dict[str, Any] | None = None) -> Any:
        """Perform HTTP GET. Separated for easy mocking."""
        import httpx

        timeout = self.config.get("timeout_seconds", 1)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

    async def query(self, request: dict[str, Any]) -> ConnectorResult:
        """
        Execute an HTTP GET request.

        Request keys:
          path (str): URL path relative to base_url.
          params (dict): Query-string parameters (optional).
          method (str): HTTP method — only GET supported for MVP (default 'GET').
        """
        path = request.get("path")
        if not path:
            return ConnectorResult(
                success=False,
                error="Request must include 'path' key",
                connector_name=self.name,
            )

        url = self._base_url() + "/" + path.lstrip("/")
        params = request.get("params")
        start = time.monotonic()
        try:
            data = await self._get(url, params)
            elapsed = int((time.monotonic() - start) * 1000)
            return ConnectorResult(
                success=True,
                data=[data],
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

    async def health_check(self) -> bool:
        try:
            result = await self.query({"path": "/health"})
            return result.success
        except Exception:
            return False
