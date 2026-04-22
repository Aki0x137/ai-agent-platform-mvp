"""FastAPI application for FinAgent MVP — T031.

Endpoints implemented in this module:
  GET  /health              — readiness check
  GET  /                    — root info
  GET  /agents              — list registered demo agents
  POST /agents/trigger      — start a reconciliation session
  GET  /sessions/{id}       — retrieve session trace
"""
from __future__ import annotations

from rich.console import Console
console = Console()



import asyncio
import os
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import structlog

from src.models import ApproveSessionRequest, HealthCheckResponse, TriggerAgentRequest

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# ── FastAPI app ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="FinAgent MVP",
    description="Internal AI Agent Platform - Local MVP",
    version="0.1.0",
)

cors_origins = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:8000"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Module-level singletons (replaceable for testing) ──────────────────────

_session_manager = None  # SessionManager instance
_audit_logger = None     # AuditLogger instance
_agent = None            # ReconciliationAgent instance
_approval_service = None # ApprovalService instance


def _get_sm():
    global _session_manager
    if _session_manager is None:
        from src.sessions.session_manager import SessionManager
        db_path = os.getenv("SESSIONS_DB", "data/sessions.db")
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        _session_manager = SessionManager(db_path=db_path)
    return _session_manager


def _get_al():
    global _audit_logger
    if _audit_logger is None:
        from src.audit.audit_logger import AuditLogger
        db_path = os.getenv("AUDIT_DB", "data/audit.db")
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        _audit_logger = AuditLogger(db_path=db_path)
    return _audit_logger


def _get_agent():
    global _agent
    if _agent is None:
        from src.core.langgraph_agent import ReconciliationAgent
        _agent = ReconciliationAgent(
            session_manager=_get_sm(),
            audit_logger=_get_al(),
        )
    return _agent


def _get_approval_service():
    global _approval_service
    if _approval_service is None:
        from src.core.approval_service import ApprovalService
        _approval_service = ApprovalService(
            session_manager=_get_sm(),
            audit_logger=_get_al(),
            agent=_get_agent(),
        )
    return _approval_service


async def _check_ollama_health() -> str:
    """Check the configured Ollama host."""
    try:
        import httpx

        base_url = os.getenv("OLLAMA_HOST", "http://ollama:11434").rstrip("/")
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
        return "healthy" if resp.status_code == 200 else "unhealthy"
    except Exception as exc:
        logger.warning("Ollama health check failed", error=str(exc))
        return "unhealthy"


async def _check_postgres_health() -> str:
    """Check the configured PostgreSQL DSN with a lightweight query."""
    dsn = os.getenv("POSTGRES_DSN", "")
    if not dsn:
        logger.warning("Postgres health check failed", error="POSTGRES_DSN is not configured")
        return "unhealthy"

    try:
        import asyncpg

        conn = await asyncpg.connect(dsn=dsn, timeout=2)
        try:
            await conn.execute("SELECT 1")
        finally:
            await conn.close()
        return "healthy"
    except Exception as exc:
        logger.warning("Postgres health check failed", error=str(exc))
        return "unhealthy"


async def _check_redis_health() -> str:
    """Check the configured Redis URL with PING."""
    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        logger.warning("Redis health check failed", error="REDIS_URL is not configured")
        return "unhealthy"

    try:
        import redis.asyncio as redis

        client = redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
        try:
            is_healthy = await client.ping()
        finally:
            close = getattr(client, "aclose", None)
            if close is not None:
                await close()
            else:
                await client.close()
        return "healthy" if is_healthy else "unhealthy"
    except Exception as exc:
        logger.warning("Redis health check failed", error=str(exc))
        return "unhealthy"


# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """Readiness check with per-dependency status."""
    ollama_status, postgres_status, redis_status = await asyncio.gather(
        _check_ollama_health(),
        _check_postgres_health(),
        _check_redis_health(),
    )

    services: Dict[str, str] = {
        "api": "healthy",
        "ollama": ollama_status,
        "postgres": postgres_status,
        "redis": redis_status,
    }

    unhealthy = sum(1 for s in services.values() if s == "unhealthy")
    if unhealthy == 0:
        status = "healthy"
    elif unhealthy <= 1:
        status = "degraded"
    else:
        status = "unhealthy"

    return HealthCheckResponse(
        status=status,
        timestamp=datetime.utcnow(),
        services=services,
        version="0.1.0",
    )


@app.get("/")
async def root():
    return {
        "name": "FinAgent MVP",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "agents": "/agents",
            "sessions": "/sessions/{session_id}",
            "approve": "/sessions/{session_id}/approve",
            "docs": "/docs",
        },
    }


# ── Agents ────────────────────────────────────────────────────────────────────

@app.get("/agents")
async def list_agents():
    """Return registered demo agents loaded from YAML config."""
    try:
        from src.config.agent_config import load_agent_config
        cfg = load_agent_config("config/reconciliation-agent.yaml")
        return {
            "agents": [
                {
                    "name": cfg.name,
                    "description": cfg.description,
                    "model_policy": cfg.model_policy,
                    "tools": cfg.tools,
                }
            ],
            "count": 1,
        }
    except Exception as exc:
        logger.error("Failed to load agent config", error=str(exc))
        return {"agents": [], "count": 0}


# ── Trigger ────────────────────────────────────────────────────────────────────

@app.post("/agents/trigger")
async def trigger_agent(request: TriggerAgentRequest):
    """Start a reconciliation session and run it synchronously in a thread.

    Returns ``session_id``, ``status``, and a short ``message``.
    """
    sm = _get_sm()
    agent = _get_agent()

    settlement_date: str = (request.params or {}).get("settlement_date", "")
    agent_name = request.agent_name or "settlement-reconciliation-agent"

    session = sm.create_session(
        agent_id=agent_name,
        input_params={
            "settlement_date": settlement_date,
            "triggered_by": request.triggered_by,
        },
    )
    session_id: str = session["id"]

    logger.info("Triggering agent", agent=agent_name, session_id=session_id)

    loop = asyncio.get_event_loop()
    try:
        final_state: Dict[str, Any] = await loop.run_in_executor(
            None, agent.run, session_id, settlement_date
        )
    except Exception as exc:
        sm.update_status(session_id, "failed", str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    refreshed = sm.get_session(session_id) or {}
    status = refreshed.get("status", final_state.get("status", "unknown"))
    needs_approval = final_state.get("needs_approval", False)

    return {
        "session_id": session_id,
        "status": status,
        "needs_approval": needs_approval,
        "message": (
            "Reconciliation complete — awaiting human approval for ticket creation."
            if needs_approval
            else "Reconciliation complete."
        ),
    }


# ── Session trace ─────────────────────────────────────────────────────────────

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Retrieve the full trace for a session."""
    sm = _get_sm()
    al = _get_al()

    session = sm.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    audit_events = al.get_events(session_id)

    from src.api.trace_view import shape_trace
    return shape_trace(session, audit_events)


@app.post("/sessions/{session_id}/approve")
async def approve_session(session_id: str, request: ApproveSessionRequest):
    """Apply an approval decision to a paused session."""
    approval_service = _get_approval_service()

    try:
        return await approval_service.decide(
            session_id=session_id,
            approved_by=request.approved_by,
            comment=request.comment,
            status=request.status.value,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
