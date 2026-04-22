# FinAgent MVP Implementation Plan

**Project Goal:** Local Docker-based MVP demonstrating core FinAgent features (Phase 1 Foundation)

**Stack:**
- **Orchestration:** LangGraph
- **Local LLM:** Ollama (Mistral 7B, Gemma 4)
- **Session Memory:** Mem0
- **Backend:** FastAPI
- **Database:** PostgreSQL (demo) + SQLite (audit logs)
- **Container:** Docker Compose
- **Testing:** Specify BDD framework

**Target Deliverables:**
1. Docker Compose setup with all services
2. Core agent orchestration engine running LangGraph
3. Model router (local Ollama + mock cloud API)
4. 6 connector implementations (PostgreSQL, REST, In-Memory, MCP invocation, Logs fetch/check, Sandboxed code execution)
5. Audit logger with immutable trace
6. Basic YAML agent configuration
7. Session viewer & API
8. Comprehensive BDD specs

## Demo Scenario

**"End-of-Day Settlement Reconciliation with Root-Cause Analysis"**

An agent investigates a payout discrepancy reported between the exchange and our internal ledger. It traces the cause, quantifies the gap, flags it, and opens a ticket — all without human intervention until the human gate.

| Step | Connector | What the agent does |
|------|-----------|--------------------|
| 1 | PostgreSQL | Read internal payout ledger for settlement date |
| 2 | REST API | Fetch exchange's settlement statement from mock HTTP server |
| 3 | InMemory | Look up FX rates and account-to-exchange ID mapping |
| 4 | Sandbox | Run Python diff script — compute net exposure, flag rows > ₹500 |
| 5 | Logs | Pull payment-gateway container logs — find timeout/retry root cause |
| 6 | MCP | Invoke Jira MCP tool — auto-create investigation ticket with findings |
| GATE | Human | Approve before ticket is filed (mock sync approval for MVP) |

This exercises every connector naturally. No forced fits.

### Why this beats a plain "payout discrepancy" scenario
- Logs connector is needed to find *why* the gap happened (root cause)
- Sandbox connector runs the actual reconciliation math (not just an LLM guess)
- MCP connector creates a traceable Jira ticket (clear write-action output)
- InMemory is the FX/account cache that makes the diff meaningful across currencies

## MVP Scope Locked

Confirmed for the first pass:
- API plus a minimal trace UI
- PostgreSQL read-only, REST, InMemory, MCP invocation, logs fetch/check, and sandboxed code execution connectors
- Real Mem0 integration
- Docker Compose local setup with pinned Python 3.11
- Hygiene checks after every major task: `uv sync`, `python -m specify specs/`, `docker compose config`

## Execution Order

1. Lock project dependencies and local Docker stack
2. Generate and seed all mock data for the demo scenario
3. Implement shared models, secrets, and config loading
4. Build model routing and payload classification (Mistral + Gemma 4)
5. Add connectors in demo order: PostgreSQL → REST → InMemory → Sandbox → Logs → MCP
6. Add Mem0 session checkpoints and audit logging
7. Wire LangGraph orchestration around the settlement reconciliation flow
8. Expose API endpoints and minimal trace UI
9. Add BDD specs and run hygiene checks after each major step

---

## Phase 0: Planning & Setup (Week 1)

### Task P0.1: MVP Scope & Decisions — LOCKED
**Status:** Completed

**Decisions Made:**
1. **Model Routing:** Per-tool-call routing (not per-agent) to maximize local/cloud flexibility
2. **Audit Log Storage:** SQLite (append-only) for MVP; extend to Postgres later
3. **Human Gates:** Placeholder that returns mock approval for MVP testing
4. **Session Duration:** Max 1 hour, checkpoint after every 2 tool calls
5. **Connector Scope:** 6 connectors — PostgreSQL (read), REST API, InMemory, MCP invocation, Logs, Sandboxed code
6. **Secret Management:** Env-vars only for MVP (no Vault service running)
7. **Demo Scenario:** End-of-Day Settlement Reconciliation with Root-Cause Analysis

**Blocks:** None — all decisions locked

---

### Task P0.2: Generate Mock Data for Demo
**Status:** Not Started

Create all fixture data the demo scenario needs before any connector is built.

**PostgreSQL seed (add to `docker/init.sql`):**
- `demo_internal_payouts` — our ledger rows: payout_id, account_id, amount_inr, currency, settled_at, status
- `demo_exchange_settlements` — exchange rows with intentional discrepancies (missing rows, FX rounding gaps, one failed entry)
- `demo_fx_rates` — currency pair rates for the settlement date

**Mock REST API server (add as a Docker service `mock-exchange-api`):**
- `GET /settlements?date={date}` → returns exchange payout JSON matching `demo_exchange_settlements`
- `GET /accounts/{id}` → returns account metadata
- Implemented with a static JSON server (e.g. `json-server` or a tiny FastAPI fixture app)

**InMemory fixtures:**
- FX rates for INR/EUR/GBP/USD loaded at startup from `config/fx_rates.json`
- Account-to-exchange-ID mapping loaded from `config/account_mapping.json`

**Mock log file:**
- `docker/fixtures/payment_gateway.log` — pre-generated log lines including a timeout event and a retry storm matching the discrepancy timestamp

**MCP stub:**
- A local MCP server stub (`docker/mcp_stub/`) that accepts a Jira-create call and writes the ticket to a local JSON file for inspection

**Hygiene check:** `uv sync` + `python -m specify specs/` + `docker compose config`

**Checkpoint:** All fixture data in place; `docker compose up` seeds the DB and starts the mock API

---

### Task P0.3: Set Up Project Structure & Dependencies
**Status:** Not Started

Create:
- `/src/` — main source code
  - `/src/core/` — orchestration engine
  - `/src/connectors/` — connector implementations
  - `/src/models/` — data models (Agent, Session, AuditLog)
  - `/src/router/` — model routing logic
  - `/src/api/` — FastAPI endpoints
  - `/src/audit/` — audit logger
- `/specs/` — BDD test files
- `/docker/` — Docker Compose files
- `/config/` — sample agent YAML configs
- `docker-compose.yml` — all services
- `pyproject.toml` — dependencies (update)
- `.env.example` — environment variables

**Checkpoint:** Project structure created, all directories present, dependencies installable

---

## Phase 1: Core Infrastructure (Week 1-2)

### Task P1.1: Docker Compose Setup
**Status:** Not Started

Create `docker-compose.yml`:
- **ollama** service: port 11434, auto-pull Mistral 7B
- **postgres** service: port 5432, demo database with sample tables
- **app** service: FastAPI backend (port 8000)
- **networks:** isolated network for all services

Verify:
- All services start without error
- Ollama health endpoint responsive
- Postgres accessible from app
- Ports don't conflict

**Checkpoint:** `docker-compose up` brings up all services, health checks pass

---

### Task P1.2: Data Models & Database Setup
**Status:** Not Started

Create in `/src/models/`:
- `Agent` — name, description, system_prompt, tools, model_policy, version
- `Session` — id, agent_id, state, created_at, updated_at, status
- `ToolCall` — session_id, tool_name, input, output, duration, model_used
- `AuditLog` — session_id, event_type, payload, timestamp, immutable=True
- `Connector` — id, type, config, credentials_ref

Create:
- SQLAlchemy models for PostgreSQL (agent registry, connector configs)
- Pydantic models for APIs
- SQLite schema for audit logs (immutable append-only)

**Tests (Specify):** Model instantiation, validation, persistence

**Checkpoint:** Models can be created, serialized, persisted to DB

---

### Task P1.3: Secrets & Environment Management
**Status:** Not Started

Create `/src/secrets/`:
- `SecretManager` — reads from env vars
- Mock Vault adapter (extends to real Vault later)
- Support for `{{env:VAR_NAME}}` and `{{vault:path}}` references

Setup `.env.example`:
- `OLLAMA_HOST=http://ollama:11434`
- `POSTGRES_DSN=postgresql://...`
- `OPENAI_API_KEY=sk-...` (mock for MVP)
- `AUDIT_DB_PATH=/data/audit.db`

**Tests (Specify):** Secret resolution, missing secret error handling

**Checkpoint:** `SecretManager` can resolve env-var and vault-style references

---

## Phase 2: Agent Orchestration Engine (Week 2-3)

### Task P2.1: Model Router Implementation
**Status:** Not Started

Create `/src/router/model_router.py`:
- `ModelRouter` class
- Route based on agent `model_policy`:
  - `sensitive` → Ollama (local; prefer Mistral for heavier reasoning, Gemma 4 for fast local demos)
  - `general` → Mock OpenAI API
  - `hybrid` → Default to local, with redaction logic and model selection between Mistral and Gemma 4
- `PayloadClassifier` (simplified: flag if "account_number", "ssn", etc. in text)

**Tests (Specify):** Route sensitive data to local, route general to API, redaction works

**Checkpoint:** ModelRouter routes calls correctly based on policy

### Task P2.1a: Local LLM Routing Demo
**Status:** Not Started

Demonstrate local model selection in Ollama:
- Mistral 7B for richer reasoning / longer context
- Gemma 4 for smaller, faster local prompts
- Route one demo request to each model so the UI/API can show the selected local model

**Tests (Specify):** Requests route to the expected local model based on policy or prompt class

**Checkpoint:** Local LLM list includes Mistral and Gemma 4 and routing is visible in traces

---

### Task P2.2: LangGraph Agent State Graph
**Status:** Not Started

Create `/src/core/langgraph_agent.py`:
- State definition: `{agent_id, session_id, messages[], tools_executed[], status, checkpoint}`
- Nodes:
  - `initialize`: Load agent config, initialize state
  - `think`: Call LLM (routed via ModelRouter) to decide next tool
  - `execute_tool`: Call selected tool via connector
  - `checkpoint`: Save state to audit log + Mem0
  - `finalize`: Mark session complete
- Edges: Build graph with conditional routing based on LLM response

**Tests (Specify):** State graph compiles, nodes execute, checkpoints save

**Checkpoint:** Agent can execute a simple 2-step workflow (think → execute → checkpoint)

---

### Task P2.3: Connector Layer (6 connectors for MVP)
**Status:** Not Started

Create `/src/connectors/`:

**Connector 1: PostgreSQL Read-Only**
- `PostgreSQLConnector`
- Demo role: read `demo_internal_payouts` and `demo_exchange_settlements` for the settlement date
- Hardcoded allowed tables (prevent unbounded queries)
- Connection pooling via SQLAlchemy

**Connector 2: REST API**
- `RESTConnector`
- Demo role: call `mock-exchange-api` → `GET /settlements?date=...` to fetch the exchange's view
- Auth: Bearer token from secrets; timeout 30 s

**Connector 3: In-Memory**
- `InMemoryConnector`
- Demo role: look up FX rates and account-to-exchange-ID mapping loaded from `config/fx_rates.json` and `config/account_mapping.json`

**Connector 4: Sandboxed Code Execution**
- `SandboxConnector`
- Demo role: run a Python reconciliation script that diffs the two datasets, converts currencies using the FX cache, computes net exposure, and returns flagged rows
- Safety rules: no network, read-only data mount, 10 s timeout, restricted to stdlib + pandas

**Connector 5: Logs Fetch / Check**
- `LogsConnector`
- Demo role: read `payment_gateway.log` fixture — surface the timeout event and retry storm whose timestamp matches the discrepancy

**Connector 6: MCP Invocation**
- `MCPConnector`
- Demo role: call the local Jira MCP stub to create an investigation ticket containing the flagged rows and log evidence
- Human gate fires here before the ticket is actually written

Each connector:
- Implements `BaseConnector` interface
- `validate_query()` before execution (security check)
- `execute()` returns `ToolResult(status, data, duration)`

**Tests (Specify):** Each connector can execute queries, validation works, errors handled

**Checkpoint:** All 6 connectors functional, queryable from orchestration engine

---

### Task P2.4: Audit Logger (Immutable)
**Status:** Not Started

Create `/src/audit/audit_logger.py`:
- `AuditLogger` class
- SQLite backend (append-only)
- Log structure:
  ```
  session_id | event_type | timestamp | payload (JSON) | tool_call_id | model_used | duration
  ```
- No update/delete operations (enforced)
- Batch write with fsync for durability

**Tests (Specify):** Logs can be written, retrieved, not deletable, timestamps accurate

**Checkpoint:** Audit logs written immutably, queryable by session_id

---

### Task P2.5: Session Manager with Mem0
**Status:** Not Started

Create `/src/sessions/session_manager.py`:
- `SessionManager` class
- Create session → generates session_id
- Save checkpoint → uses Mem0 for semantic memory
- Retrieve session → fetch from Mem0 + audit logs
- Mem0 stores agent reasoning & context for resumption

**Tests (Specify):** Sessions created, checkpointed, retrieved, resumable

**Checkpoint:** Can create, save, and resume sessions with full state

---

## Phase 3: API & Configuration Layer (Week 3)

### Task P3.1: Agent Configuration (YAML Parser)
**Status:** Not Started

Create `/src/config/agent_config.py`:
- `AgentConfig` — parse YAML into pydantic model
- Validate: required fields (name, tools, model_policy), tool existence
- Support templating: `{{vault:path}}`, `{{env:VAR}}`

Example MVP agent config:
```yaml
name: demo-reconciliation
model_policy: hybrid
system_prompt: |
  Compare ledger entries. Flag discrepancies > ₹100.
tools:
  - postgres.read_ledger
  - rest_api.compare_dw
human_gates:
  - after: flag_discrepancy
max_session_hours: 1
```

**Tests (Specify):** Config parses, validates, template resolution works, invalid config rejected

**Checkpoint:** Can load agent configs from YAML files

---

### Task P3.2: FastAPI Backend
**Status:** Not Started

Create `/src/api/main.py`:
- `POST /agents/trigger` — start new session
  - Input: `{agent_id, params}`
  - Output: `{session_id, status}`
- `GET /sessions/{session_id}` — get session status & trace
  - Output: `{session_id, agent_id, status, tool_calls[], audit_log[]}`
- `GET /agents` — list all agents
- `POST /agents/register` — register new agent from YAML
- `GET /health` — readiness check

**Tests (Specify):** All endpoints return correct responses, error handling works

**Checkpoint:** All API endpoints working, can trigger and query sessions

---

### Task P3.3: Integration Test — End-to-End Workflow
**Status:** Not Started

Create `/specs/e2e_agent_spec.py`:
- Initialize an agent (reconciliation example)
- Trigger it via API
- Verify it makes tool calls
- Verify checkpoints saved to Mem0
- Verify audit logs immutable
- Retrieve session and validate trace

**Tests (Specify):** E2E workflow passes, all components integrate

**Checkpoint:** Can run a complete agent workflow from trigger to completion

---

## Phase 4: UI & Observability (Week 4)

### Task P4.1: Minimal Web UI
**Status:** Not Started

Create `/src/ui/` (simple Jinja2 templates):
- `/agents` — list registered agents
- `/agents/<id>/run` — form to trigger agent, submit params
- `/sessions/<id>` — view session trace, audit log, tool calls
  - Timeline view: each tool call with input/output
  - Model used indicator (Ollama vs API)
  - Checkpoint markers

**Checkpoint:** UI pages render, can view session traces

---

### Task P4.2: Session Trace Viewer (JSON UI)
**Status:** Not Started

Create `/src/api/trace_viewer.py`:
- `GET /sessions/{session_id}/trace` — returns structured trace JSON
  - Tool calls with timing
  - Model routing decisions
  - Audit events

Create simple JS frontend to visualize:
- Timeline
- Tool call inputs/outputs (with redaction indicators)
- Model routing decision tree

**Checkpoint:** Can view full session trace in web UI

---

### Task P4.3: Logging & Metrics
**Status:** Not Started

- Wire up structured logging (Python logging module)
- Prometheus metrics:
  - `agent_tool_calls_total`
  - `agent_session_duration_seconds`
  - `model_router_calls_by_policy`
- Health endpoint includes metric summaries

**Checkpoint:** Logging structured, metrics exportable

---

## Phase 5: Testing & Documentation (Week 4)

### Task P5.1: Comprehensive BDD Specs
**Status:** Not Started

Create specs for:
- Model routing decisions
- All 3 connectors (happy path + error cases)
- Session checkpointing & resumption
- Audit log immutability
- Agent configuration validation
- API endpoints (success + error responses)
- E2E workflows

Run: `python -m specify specs/` → all green

**Checkpoint:** 80%+ code coverage, all specs passing

---

### Task P5.2: Documentation
**Status:** Not Started

Create:
- `README.md` — quickstart, architecture diagram, local setup
- `/docs/API.md` — endpoint documentation
- `/docs/AGENT_CONFIG.md` — YAML schema with examples
- `/docs/DEVELOPMENT.md` — how to add new connectors, extend router
- `/docs/ARCHITECTURE.md` — component overview, data flow
- `DEPLOYMENT.md` — how to run in production (future)

**Checkpoint:** All docs complete, runnable via `docker-compose up`

---

## Checkpoints Summary

| Checkpoint | Phase | Status | Verification |
|-----------|-------|--------|--------------|
| **CP-1** | P0 | Not Started | All scope decisions made & documented |
| **CP-2** | P1 | Not Started | `docker-compose up` all healthy |
| **CP-3** | P1 | Not Started | Models persist to DB, audit logs append-only |
| **CP-4** | P1 | Not Started | SecretManager resolves env & vault refs |
| **CP-5** | P2 | Not Started | ModelRouter routes by policy correctly |
| **CP-6** | P2 | Not Started | LangGraph 2-step workflow completes |
| **CP-7** | P2 | Not Started | All 3 connectors execute & return results |
| **CP-8** | P2 | Not Started | Sessions checkpoint & resume |
| **CP-9** | P3 | Not Started | Agent config YAML parses & validates |
| **CP-10** | P3 | Not Started | FastAPI endpoints work, E2E workflow runs |
| **CP-11** | P4 | Not Started | Web UI renders session traces |
| **CP-12** | P5 | Not Started | All BDD specs green, docs complete |

---

## Cross-Cutting Task: Basic Hygiene Checks

Run this after every major milestone before moving to the next task:

1. `uv sync`
2. `python -m specify specs/`
3. `docker compose config`

If any of these fail, fix the issue before continuing.

---

## Questions for Clarification

**Before proceeding to implementation (Phase 1), please answer:**

1. **Model Routing per-tool vs per-agent?**
   - Option A: Per-agent (simpler, MVP choice)
   - Option B: Per-tool (more flexible, more complex)

2. **Human Gate Implementation:**
   - Option A: Async approval (Slack bot or email link)
   - Option B: Synchronous mock approval (for MVP)
   - Option C: Skip for MVP, add in Phase 2

3. **Session Resumption:**
   - Option A: Full resumption from checkpoint (implement Mem0)
   - Option B: Replay tool calls from audit log only
   - Option C: Simple in-memory sessions (lose on restart)

4. **UI Complexity:**
   - Option A: Minimal (just trace viewer, no builder UI)
   - Option B: Include simple agent builder (drag-drop tools)
   - Option C: YAML-only, no UI for MVP

5. **Deployment Target:**
   - Option A: localhost docker-compose only
   - Option B: Support Kubernetes (minikube)
   - Option C: Cloud-ready (but run locally for MVP)

6. **Data Persistence:**
   - Option A: SQLite only (simple, portable)
   - Option B: PostgreSQL + SQLite
   - Option C: Full Vault + PostgreSQL (production-ready)

---

**Next:** Confirm scope decisions, then start Phase 1 infrastructure work.
