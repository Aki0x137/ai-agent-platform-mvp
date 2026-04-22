# FinAgent MVP — Internal AI Agent Platform

A local Docker-based MVP of **FinAgent**, an internal AI agent platform for automating multi-step workflows across data warehouses, APIs, and core banking systems.

**Current Status:** MVP Implementation Complete
**Stack:** LangGraph + Ollama + SQLite + FastAPI + PostgreSQL + Redis  
**Demo Scenario:** End-of-Day Settlement Reconciliation with Root-Cause Analysis

---

## 📋 Current Phase

**MVP Complete**. The project correctly implements a working LangGraph orchestration layer parsing hybrid payloads via a ModelRouter directly onto local Mistral/Gemma models. All connectors are strictly functional for demonstration, including PostgreSQL for core banking, REST APIs for external exchange datasets, and an SQLite session manager recording complete ReAct audit logs.

**Refer to [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) for the full task breakdown and current phase status.**

---

---

## 🎯 Quick Start & Demo (Phase 7 Complete)

### Prerequisites
- Docker & Docker Compose (v2+)
- Python 3.11+
- `uv` package manager

### 1. Setup & Environment

Clone the repository and prepare the config:
```bash
cp .env.example .env
```

Install Python dependencies:
```bash
uv venv
source .venv/bin/activate
uv sync
```

### 2. Start Services & Database

Run PostgreSQL, Redis, and FastAPI API Server (and Ollama, if running in container):
```bash
docker compose up -d
```

Verify services are healthy:
```bash
curl http://localhost:8000/health
```

### 3. Bootstrap Local Models (Ollama)

Initialize the LLMs used by the dynamic agent:
```bash
docker compose exec ollama ollama pull mistral
docker compose exec ollama ollama pull gemma:2b
```

Run a latency validation script to confirm they return non-empty responses:
```bash
uv run python data/validate_model_latency.py --iterations 1
```

*(Note: If running Ollama natively on macOS/Windows, execute `ollama serve` then `ollama pull mistral` outside of Docker).*

### 4. Run the Demo Test Suite

End-to-end BDD tests validate the full graph orchestration and all 6 data connectors dynamically matching discrepancies:
```bash
PYTHONPATH=. uv run python -m specify specs/*_spec.py
```
*Expected: 78 tests pass.*

### 5. Trigger a Core Reconciliation Run (Live API)

Alternatively, you can run the automated interactive Python script:
```bash
python run_demo.py
```

```bash
  -H 'Content-Type: application/json' \
  -d '{"agent_name":"settlement-reconciliation-agent","params":{"settlement_date":"2026-04-20"}}'
```

### 6. View Trace & Audit Artifacts

Substitute `<session_id>` with the run returned from the previous step:
```bash
curl http://localhost:8000/sessions/<session_id>
```

### 7. Approve the Paused Session

The run will halt at a human approval gate if discrepancies are above ₹500:
```bash
curl -X POST http://localhost:8000/sessions/<session_id>/approve \
  -H 'Content-Type: application/json' \
  -d '{"approved_by":"demo-user","comment":"Proceed with Jira ticket creation"}'
```

After approval, the agent completes the LangGraph run by creating a Jira artifact via the MCP Connector.

## 🧪 Testing with Specify BDD

Run all tests:
```bash
python -m specify specs/
```

Run a single test file:
```bash
python -m specify specs/router_spec.py
```

Test coverage (stubs only, not implemented):
- ⬜ **PayloadClassifier** — Sensitivity detection (SSN, account #, credit card, PII)
- ⬜ **ModelRouter** — Routing decisions (sensitive→local, general→cloud, hybrid→per-call)
- ⬜ Connectors (coming)
- ⬜ Session Manager (coming)

---

## 📁 Project Structure

```
src/
├── models/          # Pydantic data models (Agent, Session, ToolCall) ✓
├── api/             # FastAPI application & endpoints ✓
├── core/            # LangGraph orchestration engine (WIP)
├── router/          # Model router & payload classifier ✓
├── secrets/         # Secret management (env/vault) ✓
├── connectors/      # Data connectors (PostgreSQL, REST, InMemory)
├── audit/           # Immutable audit logger
└── sessions/        # Session manager with SQLite

specs/               # BDD tests using Specify framework
├── router_spec.py   # Model router & classifier tests ✓
└── *_spec.py        # (More specs coming)

docker/
├── Dockerfile       # FastAPI app container ✓
└── init.sql         # PostgreSQL initialization ✓

config/
├── reconciliation-agent.yaml  # Sample agent config
```

---

## 📋 Implementation Status

- ✅ Python 3.11 pinned via `.python-version` and `pyproject.toml`
- ✅ uv project initialized with 50+ dependencies pinned
- ✅ Docker Compose structure defined (Ollama, PostgreSQL, Redis, FastAPI)
- ✅ Data models scaffolded (Pydantic, SQLAlchemy)
- ✅ Model Router skeleton with routing strategy
- ✅ Payload Classifier patterns defined
- ✅ Secrets Manager design (env var only for MVP)
- ✅ FastAPI app structure with health endpoint
- ✅ 6-connector architecture defined (PostgreSQL, REST, InMemory, Sandbox, Logs, MCP)
- ✅ BDD testing framework (Specify) selected and configured
- ✅ PostgreSQL schema prepared (agent registry, demo tables, connectors)
- ✅ Environment variables documented (.env, .env.example)
- ✅ Settlement reconciliation demo scenario locked
- ✅ IMPLEMENTATION_PLAN.md with full phase breakdown

## ⏭️ Next: Phase 0.2 — Generate Mock Data

Once signed off, the first implementation task is:
1. Seed PostgreSQL with settlement demo data (internal payouts, exchange settlements, FX rates)
2. Create mock REST API service for exchange data
3. Create fixture files for InMemory and Logs connectors
4. Set up MCP stub for Jira ticket creation

After that: connectors → orchestration → API → E2E testing

---

## 📚 Documentation

- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) — Full task breakdown
- [SPECIFY_GUIDE.md](./SPECIFY_GUIDE.md) — BDD framework guide
- [docs/prd.md](./docs/prd.md) — Full PRD
