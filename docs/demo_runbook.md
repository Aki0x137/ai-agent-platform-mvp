# FinAgent Demo Runbook

This document is the presenter-friendly version of the demo flow. It gives the exact commands to run, in order, and explains what each step is proving conceptually.

## Demo Goal

The demo shows five things:

1. The local platform boots cleanly.
2. The API exposes a healthy, typed orchestration surface.
3. A reconciliation workflow runs through deterministic LangGraph nodes.
4. The run pauses at a human approval gate when variance crosses the configured threshold.
5. After approval, the system creates a ticket through MCP and completes the session.

## 1. Start The Stack

Command:

```bash
docker compose build --no-cache app && docker compose up -d
```

What you are doing conceptually:

You are booting the full local demo environment: FastAPI, PostgreSQL, Redis, Ollama, and the mock exchange service. This proves the platform is self-contained and can run as a local orchestration sandbox.

What to say:

"We start the local control plane first. This gives us the API boundary, state storage, health checks, and the supporting services the agent depends on."

## 2. Verify Health

Command:

```bash
curl http://localhost:8000/health
```

What you are doing conceptually:

You are confirming the orchestration API is live and that the app can see its backing services. This is the platform readiness check before any agent workflow is triggered.

What to look for:

- `status: "healthy"`
- service entries for `api`, `ollama`, `postgres`, and `redis`

What to say:

"Before triggering any workflow, we verify that the control layer and the dependencies are healthy. This is the gate that tells us the platform can safely accept work."

## 3. Run The Interactive Demo Script

Command:

```bash
uv run python run_demo.py
```

What you are doing conceptually:

You are running the scripted happy-path demo that exercises the real API in sequence. The script is not mocking the flow. It calls the live endpoints and prints the execution stages in a presenter-friendly way.

What happens during this script:

1. It checks API health.
2. It triggers the reconciliation agent.
3. It fetches the session trace.
4. It submits the human approval.
5. It prints the completion state and ticket details.

What to say:

"This script is just a thin presenter wrapper over the real API. It lets us show the orchestration flow, the pause, and the resume behavior without manually typing each endpoint call."

## 4. Explain The Trigger Step

API command behind the script:

```bash
curl -X POST http://localhost:8000/agents/trigger \
  -H 'Content-Type: application/json' \
  -d '{"agent_name":"settlement-reconciliation-agent","params":{"settlement_date":"2026-04-20"}}'
```

What you are doing conceptually:

This starts a new session and invokes the LangGraph workflow. The API creates a session record, marks it running, and executes the graph over the seeded reconciliation data.

What to say:

"This is the entry point into the workflow. We create a session, attach inputs, and then execute the graph. From here on, every meaningful step becomes traceable."

## 5. Explain The Reconciliation Phase

No extra command is required here if you are using the script.

What the system is doing conceptually:

The graph moves through deterministic nodes:

1. `load_data`
2. `reconcile`
3. `check_gate`

The workflow loads seeded internal and exchange records, applies FX conversion, computes discrepancies, and decides whether a human gate is required.

What to say:

"This part is intentionally deterministic. We are not using an LLM to do arithmetic or core reconciliation logic. The system computes the result, measures variance in INR, and only then decides whether human review is required."

## 6. Inspect The Session Trace

Command:

```bash
curl http://localhost:8000/sessions/<session_id>
```

Replace `<session_id>` with the value returned by the trigger response.

What you are doing conceptually:

You are retrieving the persisted execution trace. This shows the session state, tool calls, audit events, and reconciliation output that were stored while the graph was running.

What to look for:

- `status: "paused"` before approval
- `tool_calls` such as `load_data` and `reconcile.run`
- `audit_events` including `checkpoint` and `human_gate`
- output summary with discrepancy counts and total variance

What to say:

"This is the observability layer. Instead of a black-box agent run, we can inspect the exact session record, the audit events, and the computed output before we let the workflow continue."

## 7. Approve The Human Gate

Command:

```bash
curl -X POST http://localhost:8000/sessions/<session_id>/approve \
  -H 'Content-Type: application/json' \
  -d '{"approved_by":"prodmanager@demo.local","comment":"Variance confirmed, proceed with Jira creation.","status":"approved"}'
```

What you are doing conceptually:

You are explicitly approving the risky action. This is the human-in-the-loop step. The platform records the approval, calls the MCP ticket connector, and transitions the session from `paused` to `completed`.

What to say:

"This is the control point. The workflow does not automatically create downstream artifacts once the threshold is breached. It pauses, waits for a human decision, and only resumes after explicit approval."

## 8. Confirm Completion

Command:

```bash
curl http://localhost:8000/sessions/<session_id>
```

What you are doing conceptually:

You are showing that the same session has now advanced to completion and contains the ticket reference generated after approval.

What to look for:

- `status: "completed"`
- ticket reference in the output payload
- final checkpoint events in the audit log

What to say:

"The important point is continuity. This is the same session before and after approval, not a second workflow. The system preserved state, recorded approval, created the ticket, and completed the run."

## Fastest Live Demo Path

If you want the shortest reliable sequence during a live presentation, use this:

```bash
docker compose build --no-cache app && docker compose up -d
curl http://localhost:8000/health
uv run python run_demo.py
```

Use the interactive prompts in `run_demo.py` to advance the flow.

## Manual API Demo Path

If you want full control and want to narrate each API call manually, use this sequence:

```bash
docker compose build --no-cache app && docker compose up -d
curl http://localhost:8000/health
curl -X POST http://localhost:8000/agents/trigger \
  -H 'Content-Type: application/json' \
  -d '{"agent_name":"settlement-reconciliation-agent","params":{"settlement_date":"2026-04-20"}}'
curl http://localhost:8000/sessions/<session_id>
curl -X POST http://localhost:8000/sessions/<session_id>/approve \
  -H 'Content-Type: application/json' \
  -d '{"approved_by":"prodmanager@demo.local","comment":"Variance confirmed, proceed with Jira creation.","status":"approved"}'
curl http://localhost:8000/sessions/<session_id>
```

## Backup Commands

If you need to troubleshoot quickly during the demo, these are the useful checks:

```bash
docker compose logs app
docker compose logs ollama
docker compose ps
```

Use these only if the main flow does not come up cleanly.