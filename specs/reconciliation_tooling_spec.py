"""BDD Specs for SandboxConnector"""
from specify import ObjectBehavior
from unittest.mock import patch
from src.connectors.sandbox_connector import SandboxConnector


class SandboxConnectorSpec(ObjectBehavior):
    """SandboxConnector executes safe reconciliation Python scripts."""

    def _let(self):
        self._describe(SandboxConnector)
        self._be_constructed_with(
            name="reconciliation_sandbox",
            config={"timeout_seconds": 30},
        )

    def it_reports_its_connector_type(self):
        """connector_type must be 'sandbox'."""
        conn = SandboxConnector(name="sb", config={})
        assert conn.connector_type == "sandbox", f"Expected sandbox, got {conn.connector_type}"

    def it_executes_reconciliation_script_and_returns_result(self):
        """query() runs a Python callable and returns its output as ConnectorResult."""
        import asyncio

        def reconcile(internal, exchange, fx_rates, account_mapping):
            return {
                "matched": [{"payout_id": "PAYOUT-1001"}],
                "missing_internal": [],
                "missing_exchange": [],
                "mismatched": [{"payout_id": "PAYOUT-1002", "variance": 51.50}],
            }

        conn = SandboxConnector(name="sb", config={"timeout_seconds": 10})
        result = asyncio.get_event_loop().run_until_complete(
            conn.query({
                "function": reconcile,
                "kwargs": {
                    "internal": [],
                    "exchange": [],
                    "fx_rates": {},
                    "account_mapping": {},
                },
            })
        )
        assert result.success, f"Expected success=True, got {result.error}"
        assert "matched" in result.data[0]

    def it_returns_failure_when_function_missing(self):
        """query() returns ConnectorResult(success=False) when no function provided."""
        import asyncio
        conn = SandboxConnector(name="sb", config={})
        result = asyncio.get_event_loop().run_until_complete(conn.query({}))
        assert not result.success
        assert result.error is not None

    def it_returns_failure_on_script_exception(self):
        """query() wraps script exceptions into ConnectorResult(success=False)."""
        import asyncio

        def bad_script(**kwargs):
            raise ValueError("divide by zero")

        conn = SandboxConnector(name="sb", config={})
        result = asyncio.get_event_loop().run_until_complete(
            conn.query({"function": bad_script, "kwargs": {}})
        )
        assert not result.success
        assert "divide by zero" in (result.error or "")
