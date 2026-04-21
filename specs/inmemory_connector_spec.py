"""BDD Specs for InMemoryConnector"""
from specify import ObjectBehavior
from src.connectors.inmemory_connector import InMemoryConnector
from src.connectors.base import ConnectorResult


class InMemoryConnectorSpec(ObjectBehavior):
    """InMemoryConnector serves fixture data from in-process dicts."""

    def _let(self):
        self._describe(InMemoryConnector)
        self._be_constructed_with(
            name="fx_rates",
            config={"source": "config/fx_rates.json"},
        )

    def it_reports_its_connector_type(self):
        """connector_type must be 'inmemory'."""
        conn = InMemoryConnector(name="fx", config={}, data={})
        assert conn.connector_type == "inmemory", f"Expected inmemory, got {conn.connector_type}"

    def it_returns_loaded_data_on_get(self):
        """query(get) returns the full dataset loaded at construction."""
        import asyncio
        conn = InMemoryConnector(
            name="fx",
            config={},
            data={"rates": {"USD": 1.0, "EUR": 0.92}},
        )
        result = asyncio.get_event_loop().run_until_complete(
            conn.query({"operation": "get"})
        )
        assert result.success, f"Expected success=True, got {result.error}"
        assert result.data[0] == {"rates": {"USD": 1.0, "EUR": 0.92}}

    def it_returns_filtered_data_on_get_with_key(self):
        """query(get, key=...) returns the value at that key."""
        import asyncio
        conn = InMemoryConnector(
            name="fx",
            config={},
            data={"rates": {"USD": 1.0, "EUR": 0.92}, "base": "USD"},
        )
        result = asyncio.get_event_loop().run_until_complete(
            conn.query({"operation": "get", "key": "rates"})
        )
        assert result.success
        assert result.data[0] == {"USD": 1.0, "EUR": 0.92}

    def it_returns_failure_for_missing_key(self):
        """query(get, key=missing) returns ConnectorResult(success=False)."""
        import asyncio
        conn = InMemoryConnector(name="fx", config={}, data={"rates": {}})
        result = asyncio.get_event_loop().run_until_complete(
            conn.query({"operation": "get", "key": "nonexistent"})
        )
        assert not result.success
        assert result.error is not None

    def it_returns_failure_for_malformed_fx_rates(self):
        """query on malformed fx data returns ConnectorResult(success=False)."""
        import asyncio
        conn = InMemoryConnector(name="fx", config={}, data=None)
        result = asyncio.get_event_loop().run_until_complete(
            conn.query({"operation": "get"})
        )
        assert not result.success
        assert result.error is not None
