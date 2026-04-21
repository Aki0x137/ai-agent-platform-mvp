"""BDD Specs for SandboxConnector and LogsConnector"""
from specify import ObjectBehavior
from unittest.mock import patch, AsyncMock
from src.connectors.sandbox_connector import SandboxConnector
from src.connectors.logs_connector import LogsConnector
from src.connectors.base import ConnectorResult


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


class LogsConnectorSpec(ObjectBehavior):
    """LogsConnector searches structured log files for payout evidence."""

    def _let(self):
        self._describe(LogsConnector)
        self._be_constructed_with(
            name="payment_gateway_logs",
            config={"log_path": "docker/fixtures/payment_gateway.log"},
        )

    def it_reports_its_connector_type(self):
        """connector_type must be 'logs'."""
        conn = LogsConnector(name="logs", config={"log_path": "/dev/null"})
        assert conn.connector_type == "logs", f"Expected logs, got {conn.connector_type}"

    def it_finds_log_entries_matching_payout_id(self):
        """query(payout_id=...) returns log lines containing that payout_id."""
        import asyncio
        log_content = (
            "2026-04-20T08:15:02Z INFO gw payout_id=PAYOUT-1002 status=queued\n"
            "2026-04-20T08:15:05Z WARN gw payout_id=PAYOUT-1002 event=webhook_timeout\n"
            "2026-04-20T08:14:57Z INFO gw payout_id=PAYOUT-1001 status=settled\n"
        )
        conn = LogsConnector(name="logs", config={"log_path": "/dev/null"})
        with patch.object(conn, "_read_log", return_value=log_content):
            result = asyncio.get_event_loop().run_until_complete(
                conn.query({"payout_id": "PAYOUT-1002"})
            )
        assert result.success, f"Expected success=True, got {result.error}"
        assert len(result.data) == 2
        assert all("PAYOUT-1002" in row["line"] for row in result.data)

    def it_returns_empty_data_when_no_matching_logs(self):
        """query() returns success with empty data when payout_id not in logs."""
        import asyncio
        conn = LogsConnector(name="logs", config={"log_path": "/dev/null"})
        with patch.object(conn, "_read_log", return_value="2026-04-20 INFO payout_id=PAYOUT-1001\n"):
            result = asyncio.get_event_loop().run_until_complete(
                conn.query({"payout_id": "PAYOUT-MISSING"})
            )
        assert result.success
        assert result.data == []

    def it_returns_failure_when_log_file_unavailable(self):
        """query() returns ConnectorResult(success=False) when log file cannot be read."""
        import asyncio
        conn = LogsConnector(name="logs", config={"log_path": "/nonexistent/path.log"})
        result = asyncio.get_event_loop().run_until_complete(
            conn.query({"payout_id": "PAYOUT-1002"})
        )
        assert not result.success
        assert result.error is not None
