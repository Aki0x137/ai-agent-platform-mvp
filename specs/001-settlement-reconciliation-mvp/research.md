# Research: FinAgent Settlement Reconciliation MVP Demo

## Decision 1: Use env-file secrets only for the MVP

- **Decision**: Store connector credentials and model configuration in `.env` and `.env.example` only.
- **Rationale**: The demo must be self-contained and runnable locally without additional infrastructure.
- **Alternatives considered**: Vault mock service. Rejected because it adds operational complexity without improving the demo narrative.

## Decision 2: Use a local mock exchange service in Docker

- **Decision**: Add a small Dockerized HTTP service that returns deterministic settlement and account payloads from local fixtures.
- **Rationale**: This preserves the REST connector story while keeping the demo reproducible.
- **Alternatives considered**: Hardcode responses in the connector. Rejected because it weakens the connector-layer demonstration.

## Decision 3: Keep model routing hybrid with a configurable secondary local model

- **Decision**: Implement hybrid routing with one required local model and one optional alternate local model defined by environment variables.
- **Rationale**: This preserves the product story without blocking setup on host-specific Ollama model availability.
- **Alternatives considered**: Hardcode Mistral plus Gemma now. Rejected because the host may not have the desired secondary tag available.

## Decision 4: Seed all demo data locally

- **Decision**: Generate PostgreSQL rows, JSON fixtures, log files, and MCP stub artifacts from local project files.
- **Rationale**: The PRD emphasizes zero external dependencies for demonstration and auditability.
- **Alternatives considered**: Live integrations. Rejected because they increase fragility and setup cost.

## Decision 5: Keep the first MVP slice focused on discrepancy investigation

- **Decision**: Deliver a complete P1 slice that computes discrepancies, returns evidence, and exposes a trace before adding approval and ticketing.
- **Rationale**: This gives a demoable MVP early while preserving the full platform story for subsequent stories.
- **Alternatives considered**: Build all connectors and human gate before any demo run. Rejected because it delays the first valuable slice.