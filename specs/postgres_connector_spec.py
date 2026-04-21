"""BDD Specs for PostgreSQLConnector"""
from specify import ObjectBehavior
from unittest.mock import patch, MagicMock, AsyncMock
from src.connectors.postgres_connector import PostgreSQLConnector
from src.connectors.base import ConnectorResult


class PostgreSQLConnectorSpec(ObjectBehavior):
    """PostgreSQLConnector reads from a PostgreSQL database."""

    def _let(self):
        self._describe(PostgreSQLConnector)
        self._be_constructed_with(
            name="demo_postgres",
            config={
                "host": "localhost",
                "port": 5432,
                "database": "finagentagent_db",
                "user": "finagentagent",
                "password": "secret",
            },
        )

    def it_reports_its_connector_type(self):
        """connector_type must be 'postgresql'."""
        conn = PostgreSQLConnector(
            name="test",
            config={"host": "localhost", "port": 5432, "database": "db", "user": "u", "password": "p"},
        )
        assert conn.connector_type == "postgresql", f"Expected postgresql, got {conn.connector_type}"

    def it_returns_a_result_on_query(self):
        """query() returns a ConnectorResult with success=True on valid SQL."""
        import asyncio
        conn = PostgreSQLConnector(
            name="test",
            config={
                "host": "localhost", "port": 5432,
                "database": "db", "user": "u", "password": "p",
            },
        )
        with patch.object(conn, "_fetch", new=AsyncMock(return_value=[{"payout_id": "P1"}])):
            result = asyncio.get_event_loop().run_until_complete(
                conn.query({"sql": "SELECT 1", "params": []})
            )
        assert isinstance(result, ConnectorResult), "Expected ConnectorResult"
        assert result.success, f"Expected success=True, got error={result.error}"
        assert result.data == [{"payout_id": "P1"}]

    def it_returns_failure_on_bad_request(self):
        """query() returns ConnectorResult(success=False) when sql key is missing."""
        import asyncio
        conn = PostgreSQLConnector(
            name="test",
            config={
                "host": "localhost", "port": 5432,
                "database": "db", "user": "u", "password": "p",
            },
        )
        result = asyncio.get_event_loop().run_until_complete(
            conn.query({})
        )
        assert not result.success, "Expected success=False for missing sql"
        assert result.error is not None

    def it_returns_failure_on_db_error(self):
        """query() wraps database exceptions into ConnectorResult(success=False)."""
        import asyncio
        conn = PostgreSQLConnector(
            name="test",
            config={
                "host": "localhost", "port": 5432,
                "database": "db", "user": "u", "password": "p",
            },
        )
        with patch.object(conn, "_fetch", new=AsyncMock(side_effect=Exception("connection refused"))):
            result = asyncio.get_event_loop().run_until_complete(
                conn.query({"sql": "SELECT 1", "params": []})
            )
        assert not result.success
        assert "connection refused" in (result.error or "")
