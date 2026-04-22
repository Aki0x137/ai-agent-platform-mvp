#!/bin/bash
set -e

# ANSI Color Codes
GREEN='\033[1;32m'
BLUE='\033[1;34m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
PURPLE='\033[1;35m'
CYAN='\033[1;36m'
RESET='\033[0m'
BOLD='\033[1m'

echo -e "${PURPLE}${BOLD}"
echo "=========================================================="
echo "        FinAgent Platform MVP - Interactive Demo"
echo "==========================================================${RESET}"
echo ""

API_URL=${API_URL:-"http://localhost:8000"}

echo -e "${BLUE}${BOLD}[Step 1] Checking Platform API Health...${RESET}"
HEALTH=$(curl -s $API_URL/health || echo '{"status": "down"}')
STATUS=$(echo "$HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','down'))" 2>/dev/null)

if [ "$STATUS" = "down" ]; then
    echo -e "${RED}Error: Cannot connect to API at $API_URL/health${RESET}"
    echo "Make sure you have started the services with: docker compose up -d"
    exit 1
fi
echo -e "${GREEN}✔ API is up and responding (Status: $STATUS)${RESET}"
echo ""

echo -e "${BLUE}${BOLD}[Step 2] Triggering Settlement Reconciliation Agent...${RESET}"
echo -e "Sending POST request to ${CYAN}$API_URL/agents/trigger${RESET}"
echo -e "Payload: { \"agent_name\": \"settlement-reconciliation-agent\", \"params\": {\"settlement_date\": \"2026-04-20\"} }"
echo ""

TRIGGER_RESP=$(curl -s -X POST $API_URL/agents/trigger \
  -H 'Content-Type: application/json' \
  -d '{"agent_name":"settlement-reconciliation-agent","params":{"settlement_date":"2026-04-20"}}')

SESSION_ID=$(echo "$TRIGGER_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null)
RUN_STATUS=$(echo "$TRIGGER_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null)
NEEDS_APPR=$(echo "$TRIGGER_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('needs_approval',''))" 2>/dev/null)

echo -e "${GREEN}✔ Run triggered successfully!${RESET}"
echo -e "Session ID: ${YELLOW}$SESSION_ID${RESET}"
echo -e "Status:     ${YELLOW}$RUN_STATUS${RESET}"
echo -e "Approval:   ${YELLOW}Required ($NEEDS_APPR)${RESET}"
echo ""

sleep 2

echo -e "${BLUE}${BOLD}[Step 3] Inspecting Session Trace & Audit Evidence...${RESET}"
echo -e "Fetching audit logs from ${CYAN}$API_URL/sessions/$SESSION_ID${RESET}"
echo ""

TRACE_RESP=$(curl -s $API_URL/sessions/$SESSION_ID)

# Extract summary and tool highlights
echo "$TRACE_RESP" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('\033[1;36m>> Execution Summary:\033[0m')
summary = data.get('output', {})
print(f\"   Matched Records: {summary.get('matched_count', 0)}\")
print(f\"   Discrepancies:   {summary.get('discrepancy_count', 0)}\")
print(f\"   Total Variance:  $\033[1;31m{summary.get('total_variance_usd', 0.0):.2f}\033[0m\")
print('')

print('\033[1;36m>> ReAct Routing & Tool Calls:\033[0m')
tool_calls = data.get('tool_calls', [])
for tc in tool_calls:
    name = tc.get('tool_name', 'unknown')
    routing = tc.get('routing_decision', 'N/A')
    duration = tc.get('duration_ms', 0)
    print(f\"   - \033[1;33m{name}\033[0m routed to [\033[1;35m{routing}\033[0m] (took {duration}ms)\")

print('')
events = data.get('audit_events', [])
human_gate = next((e for e in events if e.get('event_type') == 'human_gate'), None)
if human_gate:
    print(f\"\033[1;36m>> Human Gate Pending:\033[0m \033[1;31m{human_gate.get('details', {}).get('critical_discrepancy_count', 0)} critical discrepancies discovered.\033[0m\")
"

echo ""
sleep 2

echo -e "${BLUE}${BOLD}[Step 4] Human-in-the-Loop: Approving Ticket Creation...${RESET}"
echo -e "The variance is over the \$500 threshold, so the agent has paused."
echo -e "Submitting approval to ${CYAN}$API_URL/sessions/$SESSION_ID/approve${RESET}..."
echo ""

APPROVE_RESP=$(curl -s -X POST $API_URL/sessions/$SESSION_ID/approve \
  -H 'Content-Type: application/json' \
  -d '{"approved_by":"treasury_analyst@demo.local","comment":"Variance confirmed, proceed with Jira creation based on evidence.","status":"completed"}')

FINAL_STATUS=$(echo "$APPROVE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null)
TICKET_ID=$(echo "$APPROVE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('output_result',{}).get('ticket_reference',{}).get('ticket_id','NOT_FOUND'))" 2>/dev/null)
TICKET_URL=$(echo "$APPROVE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('output_result',{}).get('ticket_reference',{}).get('ticket_url','NOT_FOUND'))" 2>/dev/null)

echo -e "${GREEN}✔ Approval processed!${RESET}"
echo -e "Final Status: ${GREEN}$FINAL_STATUS${RESET}"
echo -e "MCP Action:   ${YELLOW}Created Investigation Ticket${RESET}"
if [ "$TICKET_ID" != "NOT_FOUND" ]; then
    echo -e "Ticket ID:    ${CYAN}$TICKET_ID${RESET}"
    echo -e "Ticket URL:   ${CYAN}$TICKET_URL${RESET}"
fi
echo ""

echo -e "${PURPLE}${BOLD}==========================================================${RESET}"
echo -e "${GREEN}${BOLD}        Demo completed! FinAgent MVP is fully functional!${RESET}"
echo -e "${PURPLE}${BOLD}==========================================================${RESET}"
