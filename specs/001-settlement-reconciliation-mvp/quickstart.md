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
  -d '{"agent_id":"settlement-reconciliation-agent","params":{"settlement_date":"2026-04-20"}}'
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