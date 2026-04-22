"""BDD Specs for RestApiConnector"""
from specify import ObjectBehavior
from unittest.mock import patch, AsyncMock
from src.connectors.rest_connector import RestApiConnector
from src.connectors.base import ConnectorResult


class RestApiConnectorSpec(ObjectBehavior):
    """RestApiConnector fetches from HTTP endpoints."""

    def _let(self):
        self._describe(RestApiConnector)
        self._be_constructed_with(
            name="mock_exchange",
            config={"base_url": "http://mock_exchange_api:8000"},
        )

    def it_reports_its_connector_type(self):
        """connector_type must be 'rest_api'."""
        conn = RestApiConnector(name="test", config={"base_url": "http://localhost:8000"})
        assert conn.connector_type == "rest_api", f"Expected rest_api, got {conn.connector_type}"

    def it_returns_data_on_successful_get(self):
        """query() returns ConnectorResult with data on HTTP 200."""
        import asyncio
        conn = RestApiConnector(
            name="test", config={"base_url": "http://localhost:8000"}
        )
        mock_response = {"settlement_date": "2026-04-20", "records": [{"payout_id": "P1"}]}
        with patch.object(conn, "_get", new=AsyncMock(return_value=mock_response)):
            result = asyncio.get_event_loop().run_until_complete(
                conn.query({"method": "GET", "path": "/settlements", "params": {"date": "2026-04-20"}})
            )
        assert result.success, f"Expected success=True, got {result.error}"
        assert result.data == [mock_response]

    def it_returns_failure_on_missing_path(self):
        """query() returns ConnectorResult(success=False) when path key is missing."""
        import asyncio
        conn = RestApiConnector(
            name="test", config={"base_url": "http://localhost:8000"}
        )
        result = asyncio.get_event_loop().run_until_complete(conn.query({}))
        assert not result.success
        assert result.error is not None

    def it_returns_failure_on_http_error(self):
        """query() wraps HTTP errors into ConnectorResult(success=False)."""
        import asyncio
        conn = RestApiConnector(
            name="test", config={"base_url": "http://localhost:8000"}
        )
        with patch.object(conn, "_get", new=AsyncMock(side_effect=Exception("connection refused"))):
            result = asyncio.get_event_loop().run_until_complete(
                conn.query({"method": "GET", "path": "/settlements"})
            )
        assert not result.success
        assert "connection refused" in (result.error or "")

    def it_handles_missing_payouts_for_a_date(self):
        """query() returns empty records list when exchange has no data for date."""
        import asyncio
        conn = RestApiConnector(
            name="test", config={"base_url": "http://localhost:8000"}
        )
        empty_response = {"settlement_date": "2026-01-01", "records": []}
        with patch.object(conn, "_get", new=AsyncMock(return_value=empty_response)):
            result = asyncio.get_event_loop().run_until_complete(
                conn.query({"method": "GET", "path": "/settlements", "params": {"date": "2026-01-01"}})
            )
        assert result.success
        assert result.data == [empty_response]
