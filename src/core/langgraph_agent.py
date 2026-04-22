
"""LangGraph state flow for settlement reconciliation — T030.

Graph topology
--------------
  load_data ──► reconcile ──► check_gate ──► (conditional)
                                                 ├── needs_approval=True  ──► await_approval ──► END
                                                 └── needs_approval=False ──► finalize        ──► END

All nodes are synchronous closures that capture the session_manager and
audit_logger so the graph can be compiled once per ReconciliationAgent
instance and invoked many times with different state.

Demo data mirrors the rows seeded in docker/init.sql so the workflow
produces deterministic, meaningful output without a live database.
"""
from __future__ import annotations

from rich.console import Console
console = Console()



import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from langgraph.graph import END, StateGraph

from src.audit.audit_logger import AuditLogger
from src.connectors import ConnectorRegistry
from src.core.reconciliation_service import ReconciliationService
from src.sessions.session_manager import SessionManager

# ── Demo fixture data (mirrors docker/init.sql seed rows) ──────────────────

DEMO_INTERNAL: List[Dict[str, Any]] = [
    {"payout_id": "PAYOUT-1001", "account_id": "ACC001", "amount_usd": 1000.00, "currency": "USD", "status": "settled"},
    {"payout_id": "PAYOUT-1002", "account_id": "ACC002", "amount_usd": 2150.25, "currency": "EUR", "status": "pending_review"},
    {"payout_id": "PAYOUT-1003", "account_id": "ACC003", "amount_usd": 780.00,  "currency": "GBP", "status": "settled"},
]

DEMO_EXCHANGE: List[Dict[str, Any]] = [
    {"payout_id": "PAYOUT-1001", "account_id": "ACC001", "amount_usd": 1000.00, "currency": "USD", "status": "settled"},
    {"payout_id": "PAYOUT-1002", "account_id": "ACC002", "amount_usd": 2098.75, "currency": "EUR", "status": "settled"},
    {"payout_id": "PAYOUT-1004", "account_id": "ACC003", "amount_usd": 120.00,  "currency": "GBP", "status": "settled"},
]

DEMO_FX_RATES: Dict[str, float] = {
    "USD": 1.0,
    "EUR": 1.08695652,
    "GBP": 1.26582278,
    "INR": 0.01198322,
}

# ── Type alias for graph state ──────────────────────────────────────────────

AgentState = Dict[str, Any]


# ── ReconciliationAgent ─────────────────────────────────────────────────────

class ReconciliationAgent:
    """LangGraph-driven reconciliation agent with audit and session tracking.

    Parameters
    ----------
    session_manager:
        ``SessionManager`` instance used to persist session lifecycle.
    audit_logger:
        ``AuditLogger`` instance used to write immutable audit events.
    threshold:
        USD variance above which a discrepancy is rated *critical* and
        triggers the human approval gate.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        audit_logger: AuditLogger,
        threshold: float = 500.0,
        mcp_connector_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.sm = session_manager
        self.al = audit_logger
        self.threshold = threshold
        self.mcp_connector_config = mcp_connector_config or {"stub_dir": "docker/mcp_stub"}
        self._graph = self._build_graph()

    # ── Graph construction ───────────────────────────────────────────────

    def _build_graph(self):
        sm = self.sm
        al = self.al
        threshold = self.threshold

        def _load_data(state: AgentState) -> AgentState:
            t0 = time.time()
            session_id: str = state["session_id"]
            console.print(f"[bold green]▶ [load_data][/bold green] Fetching internal and exchange records...")
            console.print(f"[bold green]▶ [load_data][/bold green] Fetching internal and exchange records...")

            internal = DEMO_INTERNAL
            exchange = DEMO_EXCHANGE
            fx_rates = DEMO_FX_RATES

            duration_ms = int((time.time() - t0) * 1000)
            tc = {
                "tool_name": "load_data",
                "duration_ms": duration_ms,
                "timestamp": datetime.utcnow().isoformat(),
                "routing_decision": "local",
                "model_used": None,
                "input": {"settlement_date": state["settlement_date"]},
                "output": {
                    "internal_count": len(internal),
                    "exchange_count": len(exchange),
                },
            }
            al.log(session_id, "tool_call", {
                "tool_name": "load_data",
                "duration_ms": duration_ms,
                "settlement_date": state["settlement_date"],
            })
            sm.add_tool_call(session_id, tc)

            return {
                **state,
                "internal_records": internal,
                "exchange_records": exchange,
                "fx_rates": fx_rates,
            }

        def _reconcile(state: AgentState) -> AgentState:
            t0 = time.time()
            session_id: str = state["session_id"]
            console.print(f"[bold green]▶ [reconcile][/bold green] Finding discrepancies...")
            console.print(f"[bold green]▶ [reconcile][/bold green] Finding discrepancies...")

            svc = ReconciliationService(discrepancy_threshold_usd=threshold)
            result = svc.reconcile(
                internal=state["internal_records"],
                exchange=state["exchange_records"],
                fx_rates=state["fx_rates"],
            )

            duration_ms = int((time.time() - t0) * 1000)
            result_dict: Dict[str, Any] = {
                "matched_count": result.matched_count,
                "discrepancy_count": result.discrepancy_count,
                "total_variance_usd": result.total_variance_usd,
                "matched": result.matched,
                "discrepancies": result.discrepancies,
            }

            tc = {
                "tool_name": "reconcile.run",
                "duration_ms": duration_ms,
                "timestamp": datetime.utcnow().isoformat(),
                "routing_decision": "local",
                "model_used": None,
                "input": {"record_count": len(state["internal_records"])},
                "output": {
                    "matched": result.matched_count,
                    "discrepancies": result.discrepancy_count,
                    "total_variance_usd": result.total_variance_usd,
                },
            }
            al.log(session_id, "checkpoint", {
                "step": "reconcile",
                "matched_count": result.matched_count,
                "discrepancy_count": result.discrepancy_count,
                "total_variance_usd": result.total_variance_usd,
                "duration_ms": duration_ms,
            })
            sm.add_tool_call(session_id, tc)

            return {**state, "reconciliation_result": result_dict}

        def _check_gate(state: AgentState) -> AgentState:
            result = state.get("reconciliation_result", {})
            console.print(f"[bold green]▶ [check_gate][/bold green] Validating discrepancies against $[red]{threshold}[/red] threshold...")
            console.print(f"[bold green]▶ [check_gate][/bold green] Validating discrepancies against $[red]{threshold}[/red] threshold...")
            discrepancies = result.get("discrepancies", [])
            critical = [d for d in discrepancies if d.get("severity") == "critical"]
            needs_approval = len(critical) > 0
            if needs_approval:
                console.print(f"  [bold red]⚠️ Human gate triggered![/bold red] Found {len(critical)} critical discrepancies.")
            else:
                console.print(f"  [bold cyan]✓ Automated reconciliation complete.[/bold cyan] No critical discrepancies.")

            al.log(state["session_id"], "human_gate", {
                "gate_name": "create_investigation_ticket",
                "status": "pending" if needs_approval else "skipped",
                "critical_discrepancy_count": len(critical),
            })

            return {**state, "needs_approval": needs_approval}

        def _route_after_gate(state: AgentState) -> str:
            return "await_approval" if state.get("needs_approval") else "finalize"

        def _persist_result(session_id: str, result: Dict[str, Any]) -> None:
            summary: Dict[str, Any] = {
                "matched_count": result.get("matched_count", 0),
                "discrepancy_count": result.get("discrepancy_count", 0),
                "total_variance_usd": result.get("total_variance_usd", 0.0),
            }
            sm.set_output(session_id, output=result, summary=summary)

        def _await_approval(state: AgentState) -> AgentState:
            _persist_result(state["session_id"], state.get("reconciliation_result", {}))
            sm.update_status(state["session_id"], "paused")
            al.log(state["session_id"], "checkpoint", {
                "step": "await_approval",
                "status": "paused",
            })
            return {**state, "status": "paused"}

        def _finalize(state: AgentState) -> AgentState:
            result = state.get("reconciliation_result", {})
            _persist_result(state["session_id"], result)
            sm.update_status(state["session_id"], "completed")
            al.log(state["session_id"], "checkpoint", {
                "step": "finalize",
                "status": "completed",
            })
            return {**state, "status": "completed"}

        # Assemble graph
        g: StateGraph = StateGraph(dict)
        g.add_node("load_data", _load_data)
        g.add_node("reconcile", _reconcile)
        g.add_node("check_gate", _check_gate)
        g.add_node("await_approval", _await_approval)
        g.add_node("finalize", _finalize)

        g.set_entry_point("load_data")
        g.add_edge("load_data", "reconcile")
        g.add_edge("reconcile", "check_gate")
        g.add_conditional_edges(
            "check_gate",
            _route_after_gate,
            {"await_approval": "await_approval", "finalize": "finalize"},
        )
        g.add_edge("await_approval", END)
        g.add_edge("finalize", END)
        return g.compile()

    # ── Public API ───────────────────────────────────────────────────────

    def run(self, session_id: str, settlement_date: str) -> Dict[str, Any]:
        """Execute the full reconciliation workflow synchronously.

        Marks the session as *running* before graph invocation and as
        *failed* if an unhandled exception occurs.

        Returns the final LangGraph state dict.
        """
        self.sm.update_status(session_id, "running")
        console.print(f"[bold blue]🚀 Starting reconciliation session [yellow]{session_id}[/yellow] for [yellow]{settlement_date}[/yellow][/bold blue]")
        console.print(f"[bold blue]🚀 Starting reconciliation session [yellow]{session_id}[/yellow] for [yellow]{settlement_date}[/yellow][/bold blue]")
        self.al.log(session_id, "checkpoint", {
            "step": "start",
            "settlement_date": settlement_date,
        })

        initial_state: AgentState = {
            "session_id": session_id,
            "settlement_date": settlement_date,
            "internal_records": [],
            "exchange_records": [],
            "fx_rates": {},
            "reconciliation_result": {},
            "status": "running",
            "needs_approval": False,
            "error": "",
        }

        try:
            final_state: AgentState = self._graph.invoke(initial_state)
            return final_state
        except Exception as exc:  # noqa: BLE001
            self.sm.update_status(session_id, "failed", str(exc))
            self.al.log(session_id, "error", {"step": "agent_run", "error": str(exc)})
            return {"status": "failed", "error": str(exc)}

    def resume_after_approval(
        self,
        session_id: str,
        approved_by: Optional[str] = None,
        comment: Optional[str] = None,
        ticket_reference: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Resume a paused session after a human approval decision."""
        session = self.sm.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id!r} not found")
        if session.get("status") != "paused":
            raise RuntimeError(f"Session {session_id!r} is not paused")
        if not session.get("output_result"):
            raise RuntimeError(f"Session {session_id!r} has no reconciliation output to finalize")

        self.sm.update_status(session_id, "running")
        output_result = dict(session.get("output_result") or {})
        if ticket_reference is not None:
            output_result["ticket_reference"] = ticket_reference
            self.sm.set_output(session_id, output=output_result, summary=session.get("summary"))
        self.al.log(session_id, "checkpoint", {
            "step": "resume_after_approval",
            "status": "running",
            "approved_by": approved_by,
            "comment": comment,
            "ticket_reference": ticket_reference,
        })
        self.sm.update_status(session_id, "completed")
        self.al.log(session_id, "checkpoint", {
            "step": "finalize_after_approval",
            "status": "completed",
        })
        return self.sm.get_session(session_id) or {"status": "completed"}

    def mark_ticket_creation_failed(
        self,
        session_id: str,
        error: str,
        approved_by: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mark a resumed session as failed after ticket creation error."""
        session = self.sm.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id!r} not found")

        output_result = dict(session.get("output_result") or {})
        output_result["ticket_error"] = error
        self.sm.set_output(session_id, output=output_result, summary=session.get("summary"))
        self.sm.update_status(session_id, "failed", error)
        self.al.log(session_id, "error", {
            "step": "ticket_creation",
            "error": error,
            "approved_by": approved_by,
            "comment": comment,
        })
        return self.sm.get_session(session_id) or {"status": "failed", "error": error}

    async def create_ticket_after_approval(self, session_id: str) -> Dict[str, Any]:
        """Create an investigation ticket for a paused session via the MCP connector."""
        session = self.sm.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id!r} not found")
        output = session.get("output_result") or {}
        connector = ConnectorRegistry.create(
            "mcp",
            name="mcp_ticketing",
            config=self.mcp_connector_config,
        )
        result = await connector.query({
            "action": "create_ticket",
            "session_id": session_id,
            "summary": f"Settlement discrepancy investigation for {session_id}",
            "evidence": output,
            "simulate_failure": self.mcp_connector_config.get("simulate_failure", False),
        })
        if not result.success:
            raise RuntimeError(result.error or "MCP ticket creation failed")
        return result.data[0]
