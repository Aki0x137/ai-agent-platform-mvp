# Data Model: FinAgent Settlement Reconciliation MVP Demo

## Entity: AgentDefinition

- **Purpose**: Stores the configuration of a runnable agent for the MVP.
- **Fields**:
  - `id`: UUID
  - `name`: string
  - `description`: string
  - `model_policy`: enum (`sensitive`, `general`, `hybrid`)
  - `tools`: list of tool identifiers
  - `human_gates`: list of gate definitions
  - `max_session_hours`: integer

## Entity: ReconciliationSession

- **Purpose**: Represents a single execution of the reconciliation workflow.
- **Fields**:
  - `id`: UUID
  - `agent_id`: UUID
  - `settlement_date`: date
  - `status`: enum (`pending`, `running`, `paused`, `completed`, `failed`)
  - `created_at`: timestamp
  - `updated_at`: timestamp
  - `started_at`: timestamp
  - `completed_at`: timestamp
  - `summary`: JSON object

## Entity: SettlementRecord

- **Purpose**: Normalized representation of an internal or exchange payout row.
- **Fields**:
  - `source`: enum (`internal`, `exchange`)
  - `payout_id`: string
  - `account_id`: string
  - `amount_usd`: decimal
  - `currency`: string
  - `settled_at`: date
  - `status`: string
  - `metadata`: JSON object

## Entity: Discrepancy

- **Purpose**: Captures a mismatch found during reconciliation.
- **Fields**:
  - `id`: UUID
  - `session_id`: UUID
  - `payout_id`: string
  - `discrepancy_type`: enum (`missing_internal`, `missing_exchange`, `amount_mismatch`, `status_mismatch`)
  - `variance_amount`: decimal
  - `severity`: enum (`info`, `warning`, `critical`)
  - `log_evidence`: list of strings
  - `recommended_action`: string

## Entity: ToolCallTrace

- **Purpose**: Immutable record of one tool invocation.
- **Fields**:
  - `id`: UUID
  - `session_id`: UUID
  - `tool_name`: string
  - `routing_decision`: string
  - `model_used`: string
  - `input_summary`: JSON object
  - `output_summary`: JSON object
  - `duration_ms`: integer
  - `created_at`: timestamp

## Entity: ApprovalDecision

- **Purpose**: Represents the state of a human gate.
- **Fields**:
  - `id`: UUID
  - `session_id`: UUID
  - `gate_name`: string
  - `status`: enum (`pending`, `approved`, `rejected`)
  - `requested_at`: timestamp
  - `resolved_at`: timestamp
  - `resolved_by`: string

## Entity: InvestigationTicket

- **Purpose**: Represents the output of the MCP ticketing step.
- **Fields**:
  - `id`: UUID
  - `session_id`: UUID
  - `external_ticket_id`: string
  - `title`: string
  - `summary`: string
  - `evidence`: JSON object
  - `created_at`: timestamp

## Relationships

- One `AgentDefinition` can create many `ReconciliationSession` records.
- One `ReconciliationSession` can produce many `Discrepancy` and `ToolCallTrace` records.
- One `ReconciliationSession` can have zero or one `ApprovalDecision` for the ticket creation gate.
- One `ReconciliationSession` can produce zero or one `InvestigationTicket`.