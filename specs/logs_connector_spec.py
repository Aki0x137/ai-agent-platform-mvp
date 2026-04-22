"""BDD Specs for LogsConnector."""
from specify import ObjectBehavior
from unittest.mock import patch

from src.connectors.logs_connector import LogsConnector


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