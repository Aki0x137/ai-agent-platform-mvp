# Quickstart: FinAgent Settlement Reconciliation MVP Demo

## Prerequisites

- Python 3.11 with `.venv` available
- Docker and Docker Compose
- `.env` copied from `.env.example`

## Run the local stack

```bash
source .venv/bin/activate
uv sync
docker compose up -d
```

## Validate local models (Phase 1.5)

```bash
source .venv/bin/activate
docker compose up -d ollama
docker compose exec ollama ollama pull mistral
docker compose exec ollama ollama pull gemma:2b
uv run python data/validate_model_latency.py --iterations 3
```

Expected result: both models return non-empty responses and a report is written to `data/generated/model_latency_report.json`.

Baseline (to update after each environment rebuild):
- mistral: p50=7370.93ms, p95=8693.56ms
- gemma:2b: p50=3568.16ms, p95=3992.91ms

## Validate the mock-data checkpoint

```bash
source .venv/bin/activate
uv run python data/generate_mock_data.py
docker compose config
python -m specify specs/
```

## Validate User Story 1

```bash
curl -X POST http://localhost:8000/agents/trigger \
  -H 'Content-Type: application/json' \
  -d '{"agent_name":"settlement-reconciliation-agent","params":{"settlement_date":"2026-04-20"}}'
```

Expected result: a session is created and later returns a discrepancy summary with log evidence.

## Validate User Story 2

```bash
curl http://localhost:8000/sessions/<session_id>
```

Expected result: the trace includes ordered tool calls, routing decisions, and audit events.

## Validate User Story 3

```bash
curl -X POST http://localhost:8000/sessions/<session_id>/approve \
  -H 'Content-Type: application/json' \
  -d '{"approved_by":"demo-user","comment":"Proceed with ticket creation"}'
```

Expected result: the session resumes and writes an MCP ticket artifact.
## Hygiene and Benchmark Checkpoint (Phase 7)

```bash
time PYTHONPATH=. uv run python -m specify specs/*_spec.py
```

Expected result: All tests (78 tests) PASS.
Target execution time: < 60.0s
Actual execution time: ~1.0s (utilizing local memory mocks and lightweight fixtures)
