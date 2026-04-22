"""BDD Specs for the reconciliation workflow (end-to-end slice)."""
from specify import ObjectBehavior
from src.core.reconciliation_service import ReconciliationService, ReconciliationResult


INTERNAL = [
    {"payout_id": "PAYOUT-1001", "account_id": "ACC001", "amount_usd": 1000.0, "currency": "USD", "status": "settled"},
    {"payout_id": "PAYOUT-1002", "account_id": "ACC002", "amount_usd": 2150.25, "currency": "EUR", "status": "pending_review"},
    {"payout_id": "PAYOUT-1003", "account_id": "ACC003", "amount_usd": 780.0, "currency": "GBP", "status": "settled"},
]

EXCHANGE = [
    {"payout_id": "PAYOUT-1001", "account_id": "ACC001", "amount_usd": 1000.0, "currency": "USD", "status": "settled"},
    {"payout_id": "PAYOUT-1002", "account_id": "ACC002", "amount_usd": 2098.75, "currency": "EUR", "status": "settled"},
    {"payout_id": "PAYOUT-1004", "account_id": "ACC003", "amount_usd": 120.0, "currency": "GBP", "status": "settled"},
]

FX_RATES = {"USD": 1.0, "EUR": 1.08695652, "GBP": 1.26582278}


class ReconciliationServiceSpec(ObjectBehavior):
    """ReconciliationService computes discrepancies between internal and exchange data."""

    def _let(self):
        self._describe(ReconciliationService)
        self._be_constructed_with(discrepancy_threshold_usd=500.0)

    def it_identifies_matched_payouts(self):
        """Payouts present in both sources with matching amounts should be matched."""
        result = ReconciliationService(discrepancy_threshold_usd=500.0).reconcile(
            internal=INTERNAL, exchange=EXCHANGE, fx_rates=FX_RATES
        )
        assert isinstance(result, ReconciliationResult)
        matched_ids = [r["payout_id"] for r in result.matched]
        assert "PAYOUT-1001" in matched_ids, f"Expected PAYOUT-1001 in matched, got {matched_ids}"

    def it_identifies_missing_from_exchange(self):
        """Payouts in internal ledger but absent from exchange should be flagged."""
        result = ReconciliationService(discrepancy_threshold_usd=500.0).reconcile(
            internal=INTERNAL, exchange=EXCHANGE, fx_rates=FX_RATES
        )
        missing_ids = [d["payout_id"] for d in result.discrepancies if d["type"] == "missing_exchange"]
        assert "PAYOUT-1003" in missing_ids, f"Expected PAYOUT-1003 missing_exchange, got {missing_ids}"

    def it_identifies_missing_from_internal(self):
        """Payouts in exchange feed but absent from internal should be flagged."""
        result = ReconciliationService(discrepancy_threshold_usd=500.0).reconcile(
            internal=INTERNAL, exchange=EXCHANGE, fx_rates=FX_RATES
        )
        missing_ids = [d["payout_id"] for d in result.discrepancies if d["type"] == "missing_internal"]
        assert "PAYOUT-1004" in missing_ids, f"Expected PAYOUT-1004 missing_internal, got {missing_ids}"

    def it_computes_variance_for_amount_mismatch(self):
        """Amount mismatch variance should be computed as abs(internal - exchange)."""
        result = ReconciliationService(discrepancy_threshold_usd=500.0).reconcile(
            internal=INTERNAL, exchange=EXCHANGE, fx_rates=FX_RATES
        )
        mismatched = [d for d in result.discrepancies if d["type"] == "amount_mismatch"]
        assert any(d["payout_id"] == "PAYOUT-1002" for d in mismatched), \
            f"Expected PAYOUT-1002 in mismatched, discrepancies={result.discrepancies}"
        payout_1002 = next(d for d in mismatched if d["payout_id"] == "PAYOUT-1002")
        assert payout_1002["variance_usd"] > 0

    def it_flags_discrepancy_above_threshold(self):
        """Discrepancy above threshold should have severity=critical."""
        result = ReconciliationService(discrepancy_threshold_usd=500.0).reconcile(
            internal=INTERNAL, exchange=EXCHANGE, fx_rates=FX_RATES
        )
        critical = [d for d in result.discrepancies if d.get("severity") == "critical"]
        assert len(critical) > 0, f"Expected at least one critical discrepancy, got {result.discrepancies}"

    def it_returns_summary_totals(self):
        """Result includes matched_count, discrepancy_count, and total_variance_usd."""
        result = ReconciliationService(discrepancy_threshold_usd=500.0).reconcile(
            internal=INTERNAL, exchange=EXCHANGE, fx_rates=FX_RATES
        )
        assert result.matched_count >= 1
        assert result.discrepancy_count >= 1
        assert result.total_variance_usd >= 0

    # ── Edge-case scenarios (T016a) ────────────────────────────────────────────

    def it_handles_empty_exchange_feed(self):
        """All internal payouts should be missing_exchange when exchange feed is empty."""
        result = ReconciliationService(discrepancy_threshold_usd=500.0).reconcile(
            internal=INTERNAL, exchange=[], fx_rates=FX_RATES
        )
        types = {d["type"] for d in result.discrepancies}
        assert "missing_exchange" in types, f"Expected missing_exchange type, got {types}"
        assert result.matched_count == 0

    def it_handles_malformed_fx_rates(self):
        """Missing FX rate for a currency should flag the payout with an error."""
        result = ReconciliationService(discrepancy_threshold_usd=500.0).reconcile(
            internal=INTERNAL, exchange=EXCHANGE, fx_rates={"USD": 1.0}  # EUR/GBP missing
        )
        # Should not raise; should produce discrepancies with fx_error flag
        assert result is not None
        errors = [d for d in result.discrepancies if d.get("fx_error")]
        assert len(errors) > 0, f"Expected fx_error discrepancies for missing currencies, got {result.discrepancies}"

    def it_handles_empty_internal_ledger(self):
        """All exchange records should be missing_internal when internal ledger is empty."""
        result = ReconciliationService(discrepancy_threshold_usd=500.0).reconcile(
            internal=[], exchange=EXCHANGE, fx_rates=FX_RATES
        )
        types = {d["type"] for d in result.discrepancies}
        assert "missing_internal" in types
        assert result.matched_count == 0
