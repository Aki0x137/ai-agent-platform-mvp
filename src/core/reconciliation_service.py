"""Reconciliation service — computes discrepancies between internal and exchange data."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ReconciliationResult:
    """Output of one reconciliation run."""

    matched: list[dict[str, Any]] = field(default_factory=list)
    discrepancies: list[dict[str, Any]] = field(default_factory=list)
    total_variance_usd: float = 0.0

    @property
    def matched_count(self) -> int:
        return len(self.matched)

    @property
    def discrepancy_count(self) -> int:
        return len(self.discrepancies)


class ReconciliationService:
    """
    Compares internal payout records against exchange settlement records.

    Both ``internal`` and ``exchange`` lists are dicts with at minimum:
      payout_id, account_id, amount_usd, currency, status

    ``fx_rates`` maps currency code → USD rate, e.g. {"EUR": 1.08695, "USD": 1.0}.

    Discrepancy dict shape:
      payout_id, type, variance_usd, severity, fx_error (bool, optional)
    """

    THRESHOLD_SEVERITY_MAP = [
        (0, "info"),
        (100, "warning"),
        (500, "critical"),
    ]

    def __init__(self, discrepancy_threshold_usd: float = 500.0) -> None:
        self.threshold = discrepancy_threshold_usd

    # ── Public API ──────────────────────────────────────────────────────────

    def reconcile(
        self,
        internal: list[dict[str, Any]],
        exchange: list[dict[str, Any]],
        fx_rates: dict[str, float],
    ) -> ReconciliationResult:
        """Run reconciliation and return a ReconciliationResult."""
        result = ReconciliationResult()

        internal_by_id = {r["payout_id"]: r for r in internal}
        exchange_by_id = {r["payout_id"]: r for r in exchange}

        all_ids = set(internal_by_id) | set(exchange_by_id)

        for pid in all_ids:
            int_rec = internal_by_id.get(pid)
            ext_rec = exchange_by_id.get(pid)

            if int_rec and ext_rec:
                self._compare(pid, int_rec, ext_rec, fx_rates, result)
            elif int_rec and not ext_rec:
                # Present internally, missing from exchange
                variance = self._to_usd(int_rec["amount_usd"], int_rec.get("currency", "USD"), fx_rates)
                result.discrepancies.append({
                    "payout_id": pid,
                    "type": "missing_exchange",
                    "variance_usd": round(variance, 2),
                    "severity": self._severity(variance),
                })
                result.total_variance_usd += variance
            else:
                # Present in exchange, missing internally
                variance = self._to_usd(ext_rec["amount_usd"], ext_rec.get("currency", "USD"), fx_rates)
                result.discrepancies.append({
                    "payout_id": pid,
                    "type": "missing_internal",
                    "variance_usd": round(variance, 2),
                    "severity": self._severity(variance),
                })
                result.total_variance_usd += variance

        result.total_variance_usd = round(result.total_variance_usd, 2)
        return result

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _compare(
        self,
        pid: str,
        int_rec: dict[str, Any],
        ext_rec: dict[str, Any],
        fx_rates: dict[str, float],
        result: ReconciliationResult,
    ) -> None:
        currency = int_rec.get("currency", "USD")
        int_usd_ok, int_usd = self._safe_to_usd(int_rec["amount_usd"], currency, fx_rates)
        ext_usd_ok, ext_usd = self._safe_to_usd(ext_rec["amount_usd"], ext_rec.get("currency", currency), fx_rates)

        if not int_usd_ok or not ext_usd_ok:
            result.discrepancies.append({
                "payout_id": pid,
                "type": "amount_mismatch",
                "variance_usd": 0.0,
                "severity": "warning",
                "fx_error": True,
            })
            return

        variance = abs(int_usd - ext_usd)
        if variance < 0.01:
            result.matched.append({"payout_id": pid, "amount_usd": int_usd})
        else:
            severity = self._severity(variance)
            result.discrepancies.append({
                "payout_id": pid,
                "type": "amount_mismatch",
                "variance_usd": round(variance, 2),
                "severity": severity,
                "internal_usd": round(int_usd, 2),
                "exchange_usd": round(ext_usd, 2),
            })
            result.total_variance_usd += variance

    def _to_usd(self, amount: float, currency: str, fx_rates: dict[str, float]) -> float:
        rate = fx_rates.get(currency, None)
        if rate is None:
            return amount  # fallback — treat as USD
        return amount * rate

    def _safe_to_usd(self, amount: float, currency: str, fx_rates: dict[str, float]) -> tuple[bool, float]:
        """Returns (ok, usd_amount). ok=False when FX rate is missing."""
        rate = fx_rates.get(currency)
        if rate is None:
            return False, 0.0
        return True, amount * rate

    def _severity(self, variance_usd: float) -> str:
        severity = "info"
        for threshold, label in self.THRESHOLD_SEVERITY_MAP:
            if variance_usd >= threshold:
                severity = label
        return severity
