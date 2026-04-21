from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SETTLEMENTS_FILE = FIXTURES_DIR / "settlements.json"
ACCOUNTS_FILE = FIXTURES_DIR / "accounts.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


app = FastAPI(
    title="FinAgent Mock Exchange API",
    version="0.1.0",
    description="Local fixture-backed HTTP service for the settlement reconciliation demo.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/settlements")
def get_settlements(date: str = Query(..., alias="date")) -> dict[str, Any]:
    payload = _load_json(SETTLEMENTS_FILE)
    if payload["settlement_date"] != date:
        return {"settlement_date": date, "records": []}
    return payload


@app.get("/accounts/{account_id}")
def get_account(account_id: str) -> dict[str, Any]:
    payload = _load_json(ACCOUNTS_FILE)
    account = payload["accounts"].get(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"account_id": account_id, **account}
