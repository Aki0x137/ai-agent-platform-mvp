# PRD: Internal AI Agent Platform (FinAgent)
**Version:** 0.1 — Draft  
**Status:** For Review  
**Owner:** Platform Engineering / AI Enablement  
**Audience:** Engineering, Product, Risk & Compliance, Data, Security

---

## 1. Problem Statement

Internal teams (analytics, ops, compliance, credit, product operations) need to automate multi-step workflows that span data warehouses, core banking systems, internal APIs, and document stores. Today this requires either custom scripting per team or outsourcing to third-party SaaS agents — both carry cost, security risk, and integration burden.

**FinAgent** is an internal, self-hosted agent platform that lets any internal team define, deploy, and run AI agents against the org's own data and APIs — with no changes required from application teams owning those systems.

---

## 2. Goals

| Goal | Metric |
|---|---|
| Reduce time to deploy a new internal agent | From months to < 1 week |
| Zero mandatory changes to source systems | Connector-side adapters only |
| All sensitive data processed on-prem or private cloud | 100% of PII / financial records |
| Full audit trail for every agent action | Audit log per tool call, per session |
| Support non-engineer teams building simple agents | Self-service via UI |

---

## 3. Non-Goals (v1)

- Customer-facing agents (external product surface)
- Real-time trading execution or order placement
- Replacing existing RPA tools already in production
- General-purpose LLM chat interface

---

## 4. Personas

**Agent Builder** — internal engineer or data analyst who defines agents, connects tools, and ships to internal clients.

**Agent Consumer** — business user (ops, compliance, product manager) who runs pre-built agents via a simple UI or Slack trigger, with no knowledge of the underlying model.

**Platform Admin** — controls model routing policy, secret management, access controls, and billing visibility.

**Application Team** — owns a source system (core banking, DW, etc.). Should not need to make code changes for FinAgent to connect to their system.

---

## 5. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FinAgent Platform                        │
│                                                                  │
│  ┌────────────┐   ┌──────────────┐   ┌──────────────────────┐  │
│  │  Agent UI  │   │  Agent API   │   │  Orchestration Engine│  │
│  │ (Builder + │──▶│ (REST/gRPC)  │──▶│  (LangGraph-based)   │  │
│  │  Consumer) │   └──────────────┘   └──────────┬───────────┘  │
│  └────────────┘                                  │              │
│                                        ┌─────────▼──────────┐  │
│                                        │   Model Router      │  │
│                                        │  (sensitive → local │  │
│                                        │   general → cloud)  │  │
│                                        └─────────┬──────────┘  │
│                                                  │              │
│  ┌───────────────────────────────────────────────▼──────────┐  │
│  │                  Connector Layer                          │  │
│  │  Core Banking │ REST APIs │ DW │ Kafka │ Docs │ DBs      │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │ VPC-isolated │ Audit Logs → SIEM │ Secrets Vault
```

---

## 6. Core Features

### 6.1 Agent Definition & Management

- Define agents via YAML config or a point-and-click UI
- Agent spec includes: name, description, system prompt, allowed tools, model policy, and human-in-the-loop gates
- Versioned agent configs stored in internal registry; promote dev → staging → prod
- Agents are referenceable by ID; consumers never touch config

**Example agent YAML:**
```yaml
name: reconciliation-agent
model_policy: hybrid           # sensitive ops → local model
system_prompt: |
  You are a reconciliation analyst. Compare ledger entries
  against DW records and flag discrepancies > ₹500.
tools:
  - core_banking.read_ledger
  - snowflake.query
  - jira.create_ticket
human_gates:
  - after: flag_discrepancy    # pause and notify human before filing ticket
max_session_hours: 4
```

---

### 6.2 Model Router (Hybrid LLM)

The platform routes each inference call based on data sensitivity — the agent author sets a policy, and the router enforces it at runtime.

| Policy | Routing | Use Case |
|---|---|---|
| `sensitive` | On-prem / private cloud model (Llama 3 / Mistral via vLLM) | Anything touching PII, account numbers, transaction data |
| `general` | Commercial API (Anthropic / OpenAI via private endpoint) | Summarization, code gen, doc parsing on non-sensitive inputs |
| `hybrid` | Per-tool-call routing based on payload classification | Default for most agents |

The payload classifier (a lightweight fine-tuned model) scans tool outputs before they are passed into a commercial model context. Any flagged field is redacted or summarized locally before leaving the VPC.

---

### 6.3 Connector Layer (Zero Source-System Change)

This is the platform's primary differentiator for internal adoption. Every connector runs on the FinAgent side. Source system teams expose nothing new.

#### 6.3.1 Connector Types

**Read-only connectors (no source change required):**

| Source | Connection Method | Auth |
|---|---|---|
| Core banking / ledger | JDBC read replica or existing reporting DB | Service account (read-only) |
| PostgreSQL / Oracle | JDBC / ODBC via connector pod | Vault-managed credentials |
| Snowflake / BigQuery / Redshift | Native cloud connector (read-only role) | Workload identity or service account key |
| Kafka topics | Consumer group subscription | SASL/SCRAM or mTLS |
| REST / GraphQL APIs | HTTP adapter with header injection | OAuth 2.0 client credentials or API key via Vault |
| SharePoint / Confluence | Graph API / REST API connectors | OAuth 2.0 |
| S3 / GCS / ADLS | Object storage SDK | IAM role or service principal |

**Write connectors (require minimal approval, not source change):**

These are limited-scope adapters. The source team grants a service account scoped write access — no code change on their side.

| Action | Method |
|---|---|
| Create Jira / ServiceNow ticket | REST API via service account |
| Send Slack / email notification | Webhook or SMTP relay |
| Write to S3 / GCS report bucket | IAM-scoped put-object |
| Insert into staging DB table | Pre-approved schema + service account |

#### 6.3.2 Connector Configuration (Agent Builder Side)

```yaml
connectors:
  - id: core_banking
    type: jdbc
    driver: oracle
    host: "{{vault:core_banking_host}}"
    credentials: "{{vault:core_banking_ro_creds}}"
    readonly: true
    query_timeout_seconds: 30
    allowed_tables:
      - gl_entries
      - account_balances
  - id: snowflake
    type: snowflake
    account: "{{vault:snowflake_account}}"
    warehouse: AGENT_WH
    database: FINANCE_DW
    schema: REPORTING
    readonly: true
```

Connectors are registered once by the Platform Admin and reused across agents. Application teams only need to grant the pre-provisioned service account access — a one-time IAM/DB admin operation.

---

### 6.4 Session & Execution Engine

- Long-running sessions: agents run for minutes to hours without timeout
- Checkpointing: session state saved after each tool call; resumes from last checkpoint on failure
- Parallel execution: multiple tool calls dispatched concurrently where the agent determines no dependency
- Human-in-the-loop gates: agent pauses at defined steps and sends a notification (Slack / email); resumes only on explicit approval
- Tool call budget: max tool calls per session configurable to prevent runaway costs
- Session isolation: each session runs in a container with no filesystem sharing between sessions

---

### 6.5 Observability & Audit

Every agent action is logged immutably. This is a compliance requirement, not optional.

**Per session, captured:**
- Session ID, agent ID, version, triggered by (user / schedule / event)
- Full tool call trace: input parameters, output (or redacted summary if sensitive), duration, model used
- Human gate events: who approved, timestamp
- Token consumption per model tier
- Errors and retry attempts

**Access:**
- Real-time trace viewer in platform UI (builder / admin)
- Exportable to SIEM (Splunk / Elastic) via log forwarder
- Immutable audit log stored for minimum 7 years (configurable per regulatory requirement)

---

### 6.6 Secrets & Credential Management

- All credentials stored in HashiCorp Vault (or cloud-native equivalent: AWS Secrets Manager / GCP Secret Manager)
- Connectors reference secrets by path; no credential in agent config or code
- Dynamic short-lived credentials where source systems support it (Vault DB secrets engine)
- Rotation handled by Vault; agents pick up new credentials transparently on next session

---

### 6.7 Access Control

| Role | Capability |
|---|---|
| Platform Admin | Manage connectors, model policy, cost budgets, all agents |
| Agent Builder | Create / edit / deploy agents within their team namespace |
| Agent Consumer | Trigger approved agents, view their own session results |
| Auditor | Read-only access to all audit logs and session traces |

- RBAC enforced at namespace level (team → agent → tool)
- SSO via existing IdP (Okta / Azure AD); no separate login
- MFA required for builder and admin roles
- Tool-level permissions: an agent can only call tools explicitly listed in its config; no lateral access

---

### 6.8 Scheduling & Triggering

Agents can be triggered by:
- Manual (UI or API call)
- Cron schedule (e.g., nightly reconciliation at 02:00 IST)
- Event trigger (Kafka message matching a filter rule)
- Webhook (from internal CI/CD, monitoring alert, or business system)

---

### 6.9 Consumer UI

A lightweight web UI for non-engineer consumers:
- See available agents (name, description, last run status)
- Trigger an agent run (optionally provide input parameters)
- View run status, outputs, and any pending human gates requiring their approval
- No visibility into system prompts, tool configs, or model routing

---

## 7. Data Flow & Security Boundaries

```
Agent Session Start
      │
      ▼
Payload Classifier (on-prem)
      │
      ├── Sensitive payload ──▶ Local vLLM (on-prem / private cloud)
      │
      └── Non-sensitive ──────▶ Commercial API (VPC → private endpoint)
                                     (redacted of any PII before leaving VPC)
      │
      ▼
Tool Call Executor
      │
      ├── Read connector ──▶ Source system (read-only service account)
      │
      └── Write connector ──▶ Target system (scoped write service account)
                                      │
                                      └── Human gate (if configured) before write
      │
      ▼
Audit Logger (immutable, async) ──▶ SIEM / long-term store
```

**Key boundaries:**
- No raw PII or financial data ever sent to commercial APIs
- All inter-service communication within VPC; external only via private endpoints
- Write operations always go through the human gate layer if configured
- Connector pods have no internet access; outbound only to registered sources

---

## 8. Open Questions / Decisions Needed

| # | Question | Owner | Needed By |
|---|---|---|---|
| 1 | Which on-prem model(s) for sensitive routing? (Llama 3.3 70B vs Mistral Large 2 vs internal fine-tune) — impacts GPU infra planning | AI Enablement + Infra | Phase 1 kickoff |
| 2 | What is the approved cloud region for commercial API calls? Does existing Anthropic / OpenAI enterprise agreement cover VPC private endpoints? | Procurement + Security | Phase 1 kickoff |
| 3 | For core banking (Oracle): will the DBA team provision a read replica or grant read-only service account on prod? Read replica preferred for performance isolation. | DBA / Core Banking team | Connector v1 |
| 4 | Kafka: are there existing consumer groups with lag alerting? FinAgent needs its own consumer group; confirm no offset conflicts with downstream consumers. | Data Platform team | Connector v1 |
| 5 | Human-in-the-loop gate delivery: Slack only, or also email? Does Slack approval require a bot in regulated channels? | Compliance + Comms | Phase 1 |
| 6 | Audit log retention: 7 years is baseline assumption. Confirm regulatory requirement per product line (lending vs payments vs product operations). | Risk & Compliance | Before GA |
| 7 | Cost attribution: should token / compute costs be charged back to consuming team's cost center? | Finance + Platform | Before GA |
| 8 | Do any source systems have rate limits on their reporting APIs or read replicas that need to be honoured at the connector layer? | Application teams | Connector v1 |

---

## 9. Phased Delivery

### Phase 1 — Foundation (Weeks 1–8)
- Core orchestration engine (LangGraph-based)
- Model router: local vLLM instance + one commercial API endpoint
- Connectors: PostgreSQL, Snowflake, REST APIs
- Secret management integration (Vault)
- Basic RBAC + SSO
- Audit logging to internal log store
- Platform Admin + Builder UI (YAML-first)

### Phase 2 — Connectivity (Weeks 9–16)
- Connectors: Core banking (Oracle JDBC read replica), Kafka consumer, S3/SharePoint
- Payload classifier for hybrid routing
- Human-in-the-loop gate (Slack approval flow)
- Scheduling (cron + webhook trigger)
- Consumer UI (non-engineer self-service)
- Audit export to SIEM

### Phase 3 — Scale & Governance (Weeks 17–24)
- Multi-agent orchestration (agents spawning sub-agents)
- Cost attribution and budget alerts per team
- Agent marketplace: approved agent templates reusable across teams
- BigQuery / Redshift connectors
- Confluence / SharePoint doc connectors with embedding pipeline
- SLA dashboards and session health alerting

---

## 10. Dependencies & Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Core banking team unable to provide read replica | Medium | High | Start with read-only service account on existing reporting schema; push replica to Phase 2 |
| On-prem GPU capacity insufficient for local model | Medium | High | Reserve cloud GPU (VPC-isolated) as fallback; evaluate quantized models |
| Payload classifier mis-routes sensitive data to commercial API | Low | Critical | Default to local model on classifier uncertainty; red-team classifier before Phase 2 goes live |
| Commercial API private endpoint availability in org's cloud region | Low | Medium | Validate with Anthropic / OpenAI account team before Phase 1 |
| Audit log volume exceeds storage plan | Medium | Medium | Compress and tier to cold storage after 90 days; retain index for search |

---

## 11. Success Criteria

| Milestone | Criterion |
|---|---|
| Phase 1 GA | 3 internal teams running agents in production |
| Phase 2 GA | Core banking and DW connectors live; zero source system code changes made |
| Phase 3 GA | 10+ teams; agent marketplace has 5+ reusable templates; full SIEM audit integration |
| Ongoing | Zero PII / financial data confirmed in commercial API call logs (verified quarterly) |