# FinAgent MVP — Internal AI Agent Platform

A local Docker-based MVP of **FinAgent**, an internal AI agent platform for automating multi-step workflows across data warehouses, APIs, and core banking systems.

**Current Status:** Phase 0 — Planning & Setup (Implementation Not Yet Started)  
**Stack:** LangGraph + Ollama + Mem0 + FastAPI + PostgreSQL + Redis  
**Demo Scenario:** End-of-Day Settlement Reconciliation with Root-Cause Analysis

---

## 📋 Current Phase

This is a **planning repository**. The project structure, Docker setup, data models, and implementation plan are locked. Code infrastructure (empty directories, stubs) is in place to structure the work, but core implementation (LangGraph orchestration, connectors, session management) is not yet started.

**Refer to [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) for the full task breakdown and current phase status.**

---

## 🎯 Quick Start (When Implementation Begins)

### Prerequisites
- Docker & Docker Compose (v2+)
- Python 3.11+
- `uv` package manager

### Setup (Local Development)

**1. Clone and prepare the environment:**
```bash
cd /path/to/ai-agent-platform-mvp
cp .env.example .env
```

**2. Install Python dependencies:**
```bash
uv venv
source .venv/bin/activate
uv sync
```

**3. Start all services:**
```bash
docker-compose up -d
```

**4. Verify all services are healthy:**
```bash
curl http://localhost:8000/health
```

**5. Run BDD tests:**
```bash
python -m specify specs/
```

**6. Bootstrap local Ollama models for demo runs:**
```bash
docker compose up -d ollama
docker compose exec ollama ollama pull mistral
docker compose exec ollama ollama pull gemma:2b
uv run python data/validate_model_latency.py --iterations 3
```

---

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
└── sessions/        # Session manager with Mem0

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

## 📋 Planning Status (Phase 0 — Complete)

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