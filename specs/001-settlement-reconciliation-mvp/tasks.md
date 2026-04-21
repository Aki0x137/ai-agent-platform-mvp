# Tasks: FinAgent Settlement Reconciliation MVP Demo

**Input**: Design documents from `/specs/001-settlement-reconciliation-mvp/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: Specify BDD specs are required for each user story and must be written before implementation for that story.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the local demo fixtures and repository structure needed for implementation.

- [X] T001 Create mock data generator in data/generate_mock_data.py
- [X] T002 [P] Create FX-rate fixture file in config/fx_rates.json
- [X] T003 [P] Create account-mapping fixture file in config/account_mapping.json
- [X] T004 [P] Create payment-gateway log fixture in docker/fixtures/payment_gateway.log
- [X] T005 Create mock exchange service scaffold in docker/mock_exchange_api/

---

## Phase 1.5: Local Model Setup and Validation

**Purpose**: Download, cache, and validate local LLM models (Mistral and Gemma) for latency benchmarking before agent implementation.

- [X] T005a Select exact local model tags for this host and update `.env.example` (`LOCAL_MODEL`, `ALTERNATE_LOCAL_MODEL`)
- [X] T005b Pull and cache Mistral model weights locally via Ollama (`ollama pull ${LOCAL_MODEL}`)
- [X] T005c Pull and cache Gemma model weights locally via Ollama (`ollama pull ${ALTERNATE_LOCAL_MODEL}`)
- [X] T005d Add model smoke-check script in `data/validate_model_latency.py` that runs one prompt against both models and verifies non-empty responses
- [X] T005e Run latency validation for both models and record baseline p50/p95 timings in `specs/001-settlement-reconciliation-mvp/quickstart.md`

**Checkpoint**: Both model weights are cached locally, both models return valid responses, and latency baseline is recorded with acceptable local-demo performance.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish shared infrastructure that blocks every user story.

- [X] T006 Update Docker services and env wiring in docker-compose.yml
- [X] T007 [P] Add base connector interface in src/connectors/base.py
- [X] T008 [P] Add connector registry and shared result models in src/connectors/__init__.py
- [X] T009 Upgrade agent-config loading and validation in src/config/agent_config.py
- [X] T010 Upgrade model router for dual local-model configuration in src/router/__init__.py
- [X] T011 Add approval and ticket response models in src/models/__init__.py

**Checkpoint**: Foundational services and shared abstractions are ready for story implementation.

---

## Phase 3: User Story 1 - Investigate Settlement Discrepancies (Priority: P1) 🎯 MVP

**Goal**: Deliver the first end-to-end discrepancy investigation flow with seeded data and evidence.

**Independent Test**: Trigger a seeded reconciliation run and verify discrepancy output with log evidence.

### Tests for User Story 1

- [ ] T012 [P] [US1] Write PostgreSQL connector Specify specs in specs/postgres_connector_spec.py
- [ ] T013 [P] [US1] Write REST connector Specify specs in specs/rest_connector_spec.py
- [ ] T014 [P] [US1] Write InMemory connector Specify specs in specs/inmemory_connector_spec.py
- [ ] T015 [P] [US1] Write Sandbox and Logs connector Specify specs in specs/reconciliation_tooling_spec.py
- [ ] T016 [US1] Write reconciliation workflow Specify spec in specs/reconciliation_workflow_spec.py
- [ ] T016a [US1] Add edge-case Specify scenarios (missing payouts, malformed FX rates, unavailable logs) in specs/reconciliation_workflow_spec.py

### Implementation for User Story 1

- [ ] T017 [P] [US1] Implement PostgreSQL connector in src/connectors/postgres_connector.py
- [ ] T018 [P] [US1] Implement REST connector in src/connectors/rest_connector.py
- [ ] T019 [P] [US1] Implement InMemory connector in src/connectors/inmemory_connector.py
- [ ] T020 [P] [US1] Implement Sandbox connector in src/connectors/sandbox_connector.py
- [ ] T021 [P] [US1] Implement Logs connector in src/connectors/logs_connector.py
- [ ] T022 [US1] Implement reconciliation service in src/core/reconciliation_service.py
- [ ] T023 [US1] Wire seeded data creation into docker/init.sql and data/generate_mock_data.py
- [ ] T024 [US1] Update placeholder agent config for discrepancy investigation in config/reconciliation-agent.yaml

**Checkpoint**: User Story 1 is demoable without ticket creation.

---

## Phase 4: User Story 2 - Review Session Trace and Audit Evidence (Priority: P2)

**Goal**: Expose immutable audit traces and session retrieval for completed runs.

**Independent Test**: Retrieve a completed session and inspect its tool trace, routing metadata, and audit events.

### Tests for User Story 2

- [ ] T025 [P] [US2] Write audit logger Specify specs in specs/audit_logger_spec.py
- [ ] T026 [P] [US2] Write session manager Specify specs in specs/session_manager_spec.py
- [ ] T027 [P] [US2] Write session trace API Specify specs in specs/session_api_spec.py
- [ ] T027a [US2] Add trace-completeness and redaction Specify scenarios for 100% tool-call visibility in specs/session_api_spec.py

### Implementation for User Story 2

- [ ] T028 [P] [US2] Implement immutable audit logger in src/audit/audit_logger.py
- [ ] T029 [P] [US2] Implement Mem0-backed session manager in src/sessions/session_manager.py
- [ ] T030 [US2] Implement LangGraph state flow for checkpoints in src/core/langgraph_agent.py
- [ ] T031 [US2] Expose session status and trace endpoints in src/api/main.py
- [ ] T032 [US2] Add minimal trace-view payload shaping in src/api/trace_view.py
- [ ] T032a [US2] Enforce trace redaction and complete tool-call duration/routing capture in src/audit/audit_logger.py and src/api/trace_view.py

**Checkpoint**: User Story 2 exposes a traceable, auditable session view.

---

## Phase 5: User Story 3 - Approve and File Investigation Ticket (Priority: P3)

**Goal**: Add the human approval gate and the MCP ticket-creation step.

**Independent Test**: Approve a pending run and verify a ticket artifact is created and linked to the session.

### Tests for User Story 3

- [ ] T033 [P] [US3] Write MCP connector Specify specs in specs/mcp_connector_spec.py
- [ ] T034 [P] [US3] Write approval-gate API Specify specs in specs/approval_api_spec.py
- [ ] T035 [US3] Write end-to-end ticketing Specify spec in specs/ticket_creation_flow_spec.py
- [ ] T035a [US3] Add MCP ticket-creation failure-path Specify scenario in specs/ticket_creation_flow_spec.py

### Implementation for User Story 3

- [ ] T036 [P] [US3] Implement MCP connector in src/connectors/mcp_connector.py
- [ ] T037 [P] [US3] Implement MCP stub output fixture in docker/mcp_stub/
- [ ] T038 [US3] Implement approval gate handling in src/core/approval_service.py
- [ ] T039 [US3] Expose approval endpoint in src/api/main.py
- [ ] T040 [US3] Extend reconciliation workflow to create tickets after approval in src/core/langgraph_agent.py
- [ ] T040a [US3] Handle MCP failure responses with auditable status updates in src/core/langgraph_agent.py and src/core/approval_service.py

**Checkpoint**: User Story 3 completes the full platform demo with a controlled write action.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T041 [P] Update README quickstart and demo instructions in README.md
- [ ] T042 [P] Add health and readiness dependency checks in src/api/main.py
- [ ] T043 Run hygiene suite and record checkpoint outputs in specs/001-settlement-reconciliation-mvp/quickstart.md
- [ ] T044 [P] Add explicit local-model bootstrap commands (`ollama serve`, pull, smoke check, latency check) to README.md and quickstart.md
- [ ] T045 Add env/local-only config validation and remove misleading Vault placeholders in docker-compose.yml, .env.example, and src/config/agent_config.py
- [ ] T046 Add benchmark step that records end-to-end run time (<60s target) in specs/001-settlement-reconciliation-mvp/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 must complete before Phase 1.5.
- Phase 1.5 (local model setup and validation) must complete before Phase 2.
- Phase 2 blocks all user stories.
- User Story 1 is the MVP and should ship first.
- User Stories 2 and 3 depend on Phase 2 and can proceed after User Story 1 is stable.
- Phase 6 depends on the stories you choose to include in the demo.

### User Story Dependencies

- **US1**: No story dependency after foundational work.
- **US2**: Depends on the US1 execution path being present so traces have meaningful data.
- **US3**: Depends on US1 discrepancy output and US2 session state handling.

### Parallel Opportunities

- T002, T003, T004 can run in parallel.
- T005b and T005c can run in parallel after T005a.
- T007, T008, T009, T010, T011 can run in parallel after T006 starts.
- Connector specs and connector implementations for US1 can run in parallel by file.
- Audit/session specs and implementation tasks in US2 can run in parallel where files do not overlap.
- MCP stub and connector implementation can run in parallel in US3.

## Implementation Strategy

### MVP First

1. Complete Phase 1, Phase 1.5, and Phase 2.
2. Complete User Story 1.
3. Validate the demo run and discrepancy report.
4. Only then add traceability and approval-driven ticketing.

### Incremental Delivery

1. Land the data and connector foundations.
2. Deliver the discrepancy investigation slice.
3. Add trace and audit views.
4. Add approval and ticket creation.
5. Run the hygiene suite after each major checkpoint.