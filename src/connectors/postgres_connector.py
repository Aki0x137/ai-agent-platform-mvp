"""PostgreSQL connector for FinAgent."""
from __future__ import annotations

import time
from typing import Any

from .base import Connector, ConnectorResult


class PostgreSQLConnector(Connector):
    """Reads from a PostgreSQL database using asyncpg."""

    @property
    def connector_type(self) -> str:
        return "postgresql"

    async def _fetch(self, sql: str, params: list[Any]) -> list[dict[str, Any]]:
        """Execute SQL and return rows as dicts. Separated for easy mocking."""
        import asyncpg  # type: ignore

        host = self.config.get("host", "localhost")
        port = self.config.get("port", 5432)
        database = self.config.get("database", "")
        user = self.config.get("user", "")
        password = self.config.get("password", "")

        conn = await asyncpg.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
        )
        try:
            rows = await conn.fetch(sql, *params)
            return [dict(row) for row in rows]
        finally:
            await conn.close()

    async def query(self, request: dict[str, Any]) -> ConnectorResult:
        """
        Execute a SQL query.

        Request keys:
          sql (str): SQL statement with $1, $2, ... placeholders.
          params (list): Positional parameters (default []).
        """
        sql = request.get("sql")
        if not sql:
            return ConnectorResult(
                success=False,
                error="Request must include 'sql' key",
                connector_name=self.name,
            )

        params: list[Any] = request.get("params", [])
        start = time.monotonic()
        try:
            rows = await self._fetch(sql, params)
            elapsed = int((time.monotonic() - start) * 1000)
            return ConnectorResult(
                success=True,
                data=rows,
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
            result = await self.query({"sql": "SELECT 1", "params": []})
            return result.success
        except Exception:
            return False
