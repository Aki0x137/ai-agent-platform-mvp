"""FastAPI application for FinAgent MVP"""
import os
from datetime import datetime
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import structlog

from src.models import HealthCheckResponse

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

# Create FastAPI app
app = FastAPI(
    title="FinAgent MVP",
    description="Internal AI Agent Platform - Local MVP",
    version="0.1.0",
)

# Configure CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health Check Endpoint
# ============================================================================

async def check_service_health(service_name: str, check_func) -> str:
    """Check individual service health"""
    try:
        await check_func()
        return "healthy"
    except Exception as e:
        logger.error(f"Service health check failed", service=service_name, error=str(e))
        return "unhealthy"


@app.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """Health check endpoint with service status"""
    # For MVP, return mock status
    # In real implementation, check actual service connectivity

    services: Dict[str, str] = {
        "ollama": "unknown",
        "postgres": "unknown",
        "redis": "unknown",
        "api": "healthy",
    }

    # Attempt to check services (mock for now)
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get("http://ollama:11434/api/tags", timeout=aiohttp.ClientTimeout(total=2)) as resp:
                    services["ollama"] = "healthy" if resp.status == 200 else "unhealthy"
            except:
                services["ollama"] = "unhealthy"
    except:
        pass

    # Determine overall status
    unhealthy_count = sum(1 for s in services.values() if s == "unhealthy")
    if unhealthy_count == 0:
        status = "healthy"
    elif unhealthy_count <= 1:
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
    """Root endpoint"""
    return {
        "name": "FinAgent MVP",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "agents": "/agents",
            "sessions": "/sessions",
            "connectors": "/connectors",
            "docs": "/docs",
        },
    }


# ============================================================================
# Placeholder Routes (to be implemented in subsequent phases)
# ============================================================================

@app.get("/agents")
async def list_agents():
    """List all agents (placeholder)"""
    return {"agents": [], "count": 0}


@app.post("/agents/trigger")
async def trigger_agent(agent_id: str, params: dict = None):
    """Trigger an agent (placeholder)"""
    raise HTTPException(status_code=501, detail="Not implemented yet")


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session trace (placeholder)"""
    raise HTTPException(status_code=501, detail="Not implemented yet")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
