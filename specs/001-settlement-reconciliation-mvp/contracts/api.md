# API Contract: FinAgent Settlement Reconciliation MVP Demo

## POST /agents/trigger

- **Purpose**: Start a reconciliation session.
- **Request Body**:
  - `agent_id`: string
  - `params.settlement_date`: string (`YYYY-MM-DD`)
- **Response**:
  - `session_id`: string
  - `status`: string
  - `message`: string

## GET /sessions/{session_id}

- **Purpose**: Retrieve session status, summary, and execution trace.
- **Response**:
  - `session_id`: string
  - `agent_id`: string
  - `status`: string
  - `summary`: object
  - `tool_calls`: array
  - `audit_events`: array
  - `pending_gate`: object or null

## POST /sessions/{session_id}/approve

- **Purpose**: Approve the pending write action for ticket creation.
- **Request Body**:
  - `approved_by`: string
  - `comment`: string
- **Response**:
  - `session_id`: string
  - `gate_status`: string
  - `next_status`: string

## GET /agents

- **Purpose**: List registered demo agents.
- **Response**:
  - Array of agent summaries with `id`, `name`, `description`, and `model_policy`

## GET /health

- **Purpose**: Readiness check for app and dependencies.
- **Response**:
  - `status`: string
  - `timestamp`: string
  - `dependencies`: object