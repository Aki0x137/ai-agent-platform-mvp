import requests
import time
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.json import JSON

console = Console()
API_URL = "http://localhost:8000"

def get_status():
    try:
        r = requests.get(f"{API_URL}/health")
        return r.json().get("status", "down") == "healthy"
    except Exception:
        return False

console.print(Panel.fit("[bold magenta]FinAgent Platform MVP - Interactive Demo[/bold magenta]", border_style="magenta"))

# Step 1: Health check
with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
    task = progress.add_task("[blue]Checking Platform API Health...", total=None)
    time.sleep(1)
    if not get_status():
        progress.stop()
        console.print("[red]Error: Cannot connect to API at localhost:8000.[/red]\nMake sure you have started services with: docker compose up -d")
        sys.exit(1)
    progress.update(task, completed=1, description="[bold green]✔ API is up and responding[/bold green]")

console.print("")
Prompt.ask("[dim]Press Enter to trigger the Settlement Reconciliation Agent...[/dim]")
console.print("\n[bold blue][Step 2] Triggering Settlement Reconciliation Agent...[/bold blue]")

try:
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("[cyan]Calling POST /agents/trigger...", total=None)
        resp = requests.post(f"{API_URL}/agents/trigger", json={"agent_name": "settlement-reconciliation-agent", "params": {"settlement_date": "2026-04-20"}})
        resp.raise_for_status()
        data = resp.json()
        progress.update(task, completed=1, description="[bold green]✔ Run triggered successfully![/bold green]")
        
    session_id = data.get("session_id")
    console.print(f"Session ID:  [bold yellow]{session_id}[/bold yellow]")
    console.print(f"Status:      [bold yellow]{data.get('status')}[/bold yellow]")
    console.print(f"Approval:    [bold yellow]Required ({data.get('needs_approval')})[/bold yellow]")

    console.print("")
    Prompt.ask(f"[dim]Press Enter to inspect the audit trace for session {session_id}...[/dim]")
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task(f"[cyan]Fetching GET /sessions/{session_id}...", total=None)
        trace_resp = requests.get(f"{API_URL}/sessions/{session_id}")
        trace_resp.raise_for_status()
        trace_data = trace_resp.json()
        progress.update(task, completed=1, description="[bold green]✔ Fetched Session Trace[/bold green]")

    console.print("\n[bold cyan]>> Execution Summary:[/bold cyan]")
    output = trace_data.get("output", {})
    console.print(f"   Matched Records: {output.get('matched_count', 0)}")
    console.print(f"   Discrepancies:   [bold red]{output.get('discrepancy_count', 0)}[/bold red]")
    console.print(f"   Total Variance:  [bold red]₹{output.get('total_variance_inr', 0.0):.2f}[/bold red]")

    console.print("\n[bold cyan]>> ReAct Routing & Tool Calls:[/bold cyan]")
    for tc in trace_data.get("tool_calls", []):
        console.print(f"   - [bold yellow]{tc.get('tool_name', 'unknown')}[/bold yellow] routed to [[bold magenta]{tc.get('routing_decision', 'N/A')}[/bold magenta]] (took {tc.get('duration_ms', 0)}ms)")

    events = trace_data.get("audit_events", [])
    human_gate = next((e for e in events if e.get("event_type") == "human_gate"), None)
    if human_gate:
        console.print(f"\n[bold cyan]>> Human Gate Pending:[/bold cyan] [bold red]{human_gate.get('details', {}).get('critical_discrepancy_count', 0)} critical discrepancies discovered. Requires manual sign-off.[/bold red]")

    console.print("")
    Prompt.ask(f"[dim]Press Enter to submit Human approval and complete the flow...[/dim]")
    
    console.print(f"\n[bold blue][Step 4] Human-in-the-Loop: Approving Ticket Creation...[/bold blue]")
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("[cyan]Calling POST /sessions/.../approve...", total=None)
        appr_resp = requests.post(
            f"{API_URL}/sessions/{session_id}/approve",
            json={"approved_by": "prodmanager@demo.local", "comment": "Variance confirmed, proceed with Jira creation.", "status": "approved"}
        )
        appr_resp.raise_for_status()
        appr_data = appr_resp.json()
        progress.update(task, completed=1, description="[bold green]✔ Approval processed![/bold green]")

    console.print(f"Final Status: [bold green]{appr_data.get('status')}[/bold green]")
    ticket_ref = appr_data.get('output_result', {}).get('ticket_reference', {})
    if ticket_ref:
        console.print(f"Ticket ID:    [bold cyan]{ticket_ref.get('ticket_id')}[/bold cyan]")
        console.print(f"Ticket URL:   [bold cyan]{ticket_ref.get('ticket_url')}[/bold cyan]")
        
    console.print("\n[bold magenta]==========================================================[/bold magenta]")
    console.print("[bold green]        Demo completed! FinAgent MVP is fully functional!     [/bold green]")
    console.print("[bold magenta]==========================================================[/bold magenta]\n")

except Exception as e:
    console.print(f"[bold red]Demo failed: {e}[/bold red]")
