"""BDD Specs for MCPConnector."""
from specify import ObjectBehavior

from src.connectors.mcp_connector import MCPConnector


class MCPConnectorSpec(ObjectBehavior):
    """MCPConnector loads deterministic local ticket stub artifacts."""

    def _let(self):
        self._describe(MCPConnector)
        self._be_constructed_with(
            name="mcp_ticketing",
            config={"stub_dir": "docker/mcp_stub"},
        )

    def it_reports_its_connector_type(self):
        """connector_type must be 'mcp'."""
        conn = MCPConnector(name="mcp", config={"stub_dir": "docker/mcp_stub"})
        assert conn.connector_type == "mcp", f"Expected mcp, got {conn.connector_type}"

    def it_returns_ticket_data_for_create_ticket(self):
        """query(create_ticket) returns a successful ticket stub payload."""
        import asyncio

        conn = MCPConnector(name="mcp", config={"stub_dir": "docker/mcp_stub"})
        result = asyncio.get_event_loop().run_until_complete(
            conn.query({
                "action": "create_ticket",
                "summary": "Mismatch over threshold",
                "evidence": {"payout_id": "PAYOUT-1002"},
                "session_id": "sess-mcp-01",
            })
        )
        assert result.success, f"Expected success=True, got {result.error}"
        assert result.data[0]["ticket_id"].startswith("INV-"), f"Unexpected ticket payload: {result.data}"

    def it_returns_failure_when_action_is_missing(self):
        """query() returns ConnectorResult(success=False) when action is not provided."""
        import asyncio

        conn = MCPConnector(name="mcp", config={"stub_dir": "docker/mcp_stub"})
        result = asyncio.get_event_loop().run_until_complete(conn.query({}))
        assert not result.success
        assert result.error is not None

    def it_returns_failure_for_stubbed_mcp_error(self):
        """query(simulate_failure=True) returns an MCP failure payload."""
        import asyncio

        conn = MCPConnector(name="mcp", config={"stub_dir": "docker/mcp_stub"})
        result = asyncio.get_event_loop().run_until_complete(
            conn.query({
                "action": "create_ticket",
                "summary": "Mismatch over threshold",
                "simulate_failure": True,
            })
        )
        assert not result.success
        assert "MCP" in (result.error or "")