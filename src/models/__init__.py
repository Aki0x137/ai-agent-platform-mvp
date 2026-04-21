"""Data models for FinAgent MVP"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


class ModelPolicy(str, Enum):
    """Model routing policy"""
    SENSITIVE = "sensitive"  # Route to local Ollama
    GENERAL = "general"       # Route to commercial API
    HYBRID = "hybrid"         # Per-tool-call routing


class SessionStatus(str, Enum):
    """Session execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class ConnectorType(str, Enum):
    """Supported connector types"""
    POSTGRESQL = "postgresql"
    REST_API = "rest_api"
    INMEMORY = "inmemory"
    MCP = "mcp"
    LOGS = "logs"
    SANDBOX = "sandbox"


# ============================================================================
# Agent Models
# ============================================================================

class AgentConfig(BaseModel):
    """Agent configuration (from YAML)"""
    name: str
    description: Optional[str] = None
    system_prompt: str
    model_policy: ModelPolicy = ModelPolicy.HYBRID
    tools: List[str]
    human_gates: Optional[List[Dict[str, Any]]] = None
    max_session_hours: int = 4

    model_config = ConfigDict(use_enum_values=True)


class Agent(BaseModel):
    """Agent entity"""
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    version: int = 1
    system_prompt: str
    model_policy: ModelPolicy = ModelPolicy.HYBRID
    tools: List[str]
    max_session_hours: int = 4
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    is_active: bool = True

    model_config = ConfigDict(use_enum_values=True)


# ============================================================================
# Session Models
# ============================================================================

class Session(BaseModel):
    """Agent session (execution context)"""
    id: UUID = Field(default_factory=uuid4)
    agent_id: UUID
    status: SessionStatus = SessionStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: Optional[str] = None
    input_params: Dict[str, Any] = Field(default_factory=dict)
    output_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    total_tool_calls: int = 0
    total_tokens_used: int = 0

    model_config = ConfigDict(use_enum_values=True)


class SessionState(BaseModel):
    """Session runtime state (for checkpointing)"""
    session_id: UUID
    agent_id: UUID
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    tools_executed: List[str] = Field(default_factory=list)
    status: SessionStatus = SessionStatus.PENDING
    checkpoint_index: int = 0
    last_checkpoint_time: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=True)


# ============================================================================
# Tool Call Models
# ============================================================================

class ToolCall(BaseModel):
    """Individual tool call record"""
    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    tool_name: str
    input_params: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    execution_duration_ms: Optional[int] = None
    model_used: Optional[str] = None  # e.g., "ollama:mistral", "openai:gpt-4"
    routing_policy: Optional[str] = None  # sensitive | general | hybrid
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    order_index: int = 0

    model_config = ConfigDict(use_enum_values=True)


class ToolResult(BaseModel):
    """Result from tool execution"""
    tool_name: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: int
    model_used: Optional[str] = None
    routing_policy: Optional[str] = None


# ============================================================================
# Audit Models
# ============================================================================

class AuditEvent(BaseModel):
    """Audit log event (immutable)"""
    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    event_type: str  # tool_call | checkpoint | human_gate | error
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: Dict[str, Any]
    tool_call_id: Optional[UUID] = None
    model_used: Optional[str] = None
    duration_ms: Optional[int] = None
    immutable_hash: Optional[str] = None  # SHA256 for integrity

    model_config = ConfigDict(use_enum_values=True)


# ============================================================================
# Connector Models
# ============================================================================

class ConnectorConfig(BaseModel):
    """Connector configuration"""
    id: UUID = Field(default_factory=uuid4)
    name: str
    type: ConnectorType
    config: Dict[str, Any]
    credentials_vault_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

    model_config = ConfigDict(use_enum_values=True)


class QueryRequest(BaseModel):
    """Query request to a connector"""
    connector_name: str
    query_type: str  # sql | rest | kafka
    query: str
    params: Optional[Dict[str, Any]] = None
    timeout_seconds: int = 30


class QueryResponse(BaseModel):
    """Response from connector query"""
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    execution_time_ms: int


# ============================================================================
# API Request/Response Models
# ============================================================================

class TriggerAgentRequest(BaseModel):
    """Request to trigger an agent"""
    agent_id: Optional[UUID] = None
    agent_name: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    triggered_by: Optional[str] = None


class TriggerAgentResponse(BaseModel):
    """Response from trigger agent"""
    session_id: UUID
    agent_id: UUID
    status: SessionStatus
    created_at: datetime


class SessionTraceResponse(BaseModel):
    """Full session trace"""
    session_id: UUID
    agent_id: UUID
    agent_name: str
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    tool_calls: List[ToolCall]
    audit_events: List[AuditEvent]
    total_duration_ms: Optional[int] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ApprovalStatus(str, Enum):
    """Human approval status for a session or action."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalDecision(BaseModel):
    """Approval decision payload."""
    session_id: UUID
    approved_by: Optional[str] = None
    status: ApprovalStatus = ApprovalStatus.PENDING
    comment: Optional[str] = None
    decided_at: Optional[datetime] = None


class TicketReference(BaseModel):
    """Ticket identifier and metadata."""
    ticket_id: str
    ticket_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[UUID] = None
    summary: Optional[str] = None


class TicketResponse(BaseModel):
    """Result of ticket creation through MCP."""
    success: bool
    ticket_reference: Optional[TicketReference] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class HealthCheckResponse(BaseModel):
    """Health check status"""
    status: str  # healthy | degraded | unhealthy
    timestamp: datetime
    services: Dict[str, str]  # service_name -> status
    version: str
