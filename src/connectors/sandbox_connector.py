"""Sandbox connector for FinAgent — runs trusted Python callables in-process."""
from __future__ import annotations

import time
from typing import Any, Callable

from .base import Connector, ConnectorResult


class SandboxConnector(Connector):
    """
    Executes a trusted Python callable (the reconciliation function).

    This is *not* a subprocess sandbox — for the MVP demo the function
    is defined in the application code and is trusted. The abstraction
    exists so the connector registry can instrument and audit the call.
    """

    @property
    def connector_type(self) -> str:
        return "sandbox"

    async def query(self, request: dict[str, Any]) -> ConnectorResult:
        """
        Run a Python callable and return its output.

        Request keys:
          function (Callable): The callable to invoke.
          kwargs (dict): Keyword arguments to pass to the callable.
        """
        func: Callable | None = request.get("function")
        if func is None or not callable(func):
            return ConnectorResult(
                success=False,
                error="Request must include a callable 'function' key",
                connector_name=self.name,
            )

        kwargs: dict[str, Any] = request.get("kwargs", {})
        start = time.monotonic()
        try:
            result = func(**kwargs)
            elapsed = int((time.monotonic() - start) * 1000)
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

    async def health_check(self) -> bool:
        return True
