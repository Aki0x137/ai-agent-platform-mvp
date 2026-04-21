# Implementation Plan: FinAgent Settlement Reconciliation MVP Demo

**Branch**: `[001-settlement-reconciliation-mvp]` | **Date**: 2026-04-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-settlement-reconciliation-mvp/spec.md`

## Summary

Build a local Docker-based MVP demo that runs an end-of-day settlement reconciliation workflow across seeded internal and exchange data, computes discrepancies, captures audit traces, and creates an investigation ticket after a human approval gate.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: FastAPI, LangGraph, Mem0, Ollama, SQLAlchemy, Redis, Specify BDD  
**Storage**: PostgreSQL for demo data and registry, SQLite for immutable audit logs, Redis for session/cache state  
**Testing**: Specify BDD via `python -m specify specs/`  
**Target Platform**: Local Linux Docker environment  
**Project Type**: Backend web service with local demo fixtures  
**Performance Goals**: Demo run completes within 60 seconds and returns a traceable result  
**Constraints**: No external SaaS dependencies for the demo; env-file secrets only; human gate required before write action  
**Scale/Scope**: One end-to-end settlement reconciliation demo flow with six connectors and minimal trace UI

## Constitution Check

The repository constitution template is not yet ratified and contains placeholders only. No enforceable project constitution gates are available, so planning follows the repository-level engineering instructions and the locked MVP decisions in the root implementation plan.

## Project Structure

### Documentation (this feature)

```text
specs/001-settlement-reconciliation-mvp/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── api.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── api/
├── audit/
├── connectors/
├── core/
├── models/
├── router/
├── secrets/
└── sessions/

specs/
├── router_spec.py
└── *_spec.py

docker/
├── Dockerfile
├── init.sql
└── fixtures/

config/
└── reconciliation-agent.yaml

data/
└── generate_mock_data.py
```

**Structure Decision**: Use the existing single-backend project layout already present in the repository. Feature documentation lives under `specs/001-settlement-reconciliation-mvp/`, while runtime code stays under `src/`, `docker/`, `config/`, and `data/`.

## Phase 0: Research Summary

- Keep secrets env-based for the MVP; do not introduce Vault.
- Use a lightweight local mock exchange service that runs in Docker and serves deterministic JSON fixtures.
- Use seeded PostgreSQL tables plus fixture files to guarantee repeatable demo outcomes.
- Keep the secondary local model configurable at implementation time so the setup is not blocked by host model availability.

## Phase 1: Design Outputs

- `research.md` documents key technology and demo decisions.
- `data-model.md` defines reconciliation sessions, settlement records, discrepancies, approvals, and tickets.
- `contracts/api.md` defines the minimal API surface needed for triggering runs, approving gates, and viewing traces.
- `quickstart.md` defines the validation path for the MVP and its checkpoints.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |