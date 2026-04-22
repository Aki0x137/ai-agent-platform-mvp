# Feature Specification: FinAgent Settlement Reconciliation MVP Demo

**Feature Branch**: `[001-settlement-reconciliation-mvp]`  
**Created**: 2026-04-21  
**Status**: Draft  
**Input**: User description: "Build a local Docker-based MVP demo for FinAgent that performs end-of-day settlement reconciliation with PostgreSQL, REST, InMemory, Sandbox, Logs, and MCP connectors, using LangGraph orchestration, SQLite session memory, FastAPI APIs, immutable audit logs, and Specify BDD specs."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Investigate Settlement Discrepancies (Priority: P1)

An internal operator triggers the reconciliation agent for a settlement date and receives a structured discrepancy report that compares internal payouts against exchange settlement data, explains the mismatch, and includes supporting log evidence.

**Why this priority**: This is the smallest end-to-end slice that proves the MVP works as a business demo. Without this flow, the platform does not demonstrate value.

**Independent Test**: Can be fully tested by starting the demo run for a seeded settlement date and confirming the system returns at least one flagged discrepancy, its computed variance, and the related log evidence without requiring manual ticket creation.

**Acceptance Scenarios**:

1. **Given** seeded internal payout data and exchange settlement data for the same date, **When** a user starts a reconciliation run, **Then** the system returns matched rows, unmatched rows, and discrepancy totals.
2. **Given** a discrepancy larger than the configured threshold, **When** the run completes, **Then** the system includes the threshold breach and root-cause evidence from logs in the result.

---

### User Story 2 - Review Session Trace and Audit Evidence (Priority: P2)

An internal builder or admin views the execution trace for a reconciliation session and sees each tool call, model routing decision, duration, and redacted output needed for audit and debugging.

**Why this priority**: The PRD requires auditability for every run. This turns the demo into a platform capability rather than a one-off script.

**Independent Test**: Can be tested by querying a completed session and verifying that the response shows tool-call order, model selection, checkpoint status, and immutable audit events.

**Acceptance Scenarios**:

1. **Given** a completed reconciliation session, **When** a user requests the session trace, **Then** the system returns the ordered tool calls with durations and model-routing metadata.
2. **Given** sensitive payload content in a tool result, **When** the trace is requested, **Then** sensitive fields are redacted in the stored or returned audit data.

---

### User Story 3 - Approve and File Investigation Ticket (Priority: P3)

An internal operator reviews a pending discrepancy, approves the action, and the system creates an investigation ticket through the MCP connector using the run findings.

**Why this priority**: This validates the human gate and controlled write action, which are core platform requirements but not required for the first demo slice.

**Independent Test**: Can be tested by running a session that reaches a discrepancy above threshold, approving the pending action, and confirming a ticket artifact is written by the MCP stub.

**Acceptance Scenarios**:

1. **Given** a completed run with a discrepancy over threshold, **When** the system reaches the approval gate, **Then** the session pauses with a pending action summary.
2. **Given** an approved pending action, **When** the MCP ticket step executes, **Then** the system records the ticket identifier and links it to the session trace.

---

### Edge Cases

- What happens when the exchange settlement feed has missing payouts for a date that exists internally?
- How does the system handle malformed or stale FX rates for one of the currencies in scope?
- What happens when logs are unavailable or do not contain an event that explains the discrepancy?
- How does the system behave if the MCP stub returns a failed ticket creation response after approval?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow a user to start a reconciliation session for a supplied settlement date.
- **FR-002**: The system MUST load internal payout records, exchange settlement records, FX rates, and account mappings for the requested run.
- **FR-003**: The system MUST compute matched, missing, and mismatched payout records and quantify the discrepancy amount.
- **FR-004**: The system MUST collect log evidence associated with a flagged discrepancy and attach it to the run output.
- **FR-005**: The system MUST route model calls according to the configured hybrid policy and record the routing decision per call.
- **FR-006**: The system MUST persist an immutable audit trail for each session, including tool inputs, outputs or redacted summaries, durations, and checkpoint events.
- **FR-007**: The system MUST expose session status and trace data through an API that can be used by a minimal trace view.
- **FR-008**: The system MUST pause before a write action that creates a ticket and require an explicit approval decision.
- **FR-009**: The system MUST create a ticket through the MCP connector after approval and record the resulting ticket reference.
- **FR-010**: The system MUST ship with mock data and local fixtures so the demo can run in Docker without external dependencies.
- **FR-011**: The system MUST store all credentials and connector configuration for the MVP in environment variables or local config files only.
- **FR-012**: The system MUST be verifiable through Specify BDD specifications and repeatable hygiene checks after each major implementation checkpoint.

### Key Entities *(include if feature involves data)*

- **Reconciliation Session**: A long-running execution context for one settlement date, including status, checkpoints, tool calls, and final output.
- **Settlement Record**: A normalized payout row from either the internal ledger or the exchange feed, including payout identifier, account, amount, currency, and settlement date.
- **Discrepancy**: A computed mismatch between internal and external settlement views, including variance, severity, evidence, and recommended action.
- **Audit Event**: An immutable record for a state transition, tool call, routing decision, or human approval event.
- **Approval Decision**: A pending or completed human gate result tied to a specific session and discrepancy threshold breach.
- **Investigation Ticket**: The structured artifact created through MCP after approval, including title, summary, evidence, and session linkage.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A seeded demo run can be started locally and return a reconciliation result in under 60 seconds on the local Docker stack.
- **SC-002**: The demo consistently identifies at least one seeded discrepancy and reports the computed variance and affected payout IDs.
- **SC-003**: 100% of tool calls made during a run are visible in the session trace with duration and routing metadata.
- **SC-004**: A pending approval can be completed and produce a ticket artifact without requiring any external SaaS dependency.

## Assumptions

- The MVP is a demo for internal stakeholders, so seeded mock data is acceptable and preferred over live system integrations.
- A lightweight local trace view is sufficient; a full production-grade builder UI is out of scope for this feature.
- Secrets for the MVP are supplied via `.env` and local config only; Vault integration is deferred.
- The local Docker environment is the primary target runtime for validation and demos.