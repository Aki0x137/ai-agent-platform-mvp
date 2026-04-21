"""Base connector abstractions for FinAgent."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional


class ConnectorResult:
    """Standard result returned by all connector implementations."""

    def __init__(
        self,
        success: bool,
        data: Optional[list[dict[str, Any]]] = None,
        error: Optional[str] = None,
        execution_time_ms: int = 0,
        connector_name: str = "",
    ) -> None:
        self.success = success
        self.data = data or []
        self.error = error
        self.execution_time_ms = execution_time_ms
        self.connector_name = connector_name

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "connector_name": self.connector_name,
        }


class Connector(ABC):
    """Base connector interface."""

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        self.name = name
        self.config = config

    @property
    @abstractmethod
    def connector_type(self) -> str:
        """Connector type identifier."""

    @abstractmethod
    async def query(self, request: dict[str, Any]) -> ConnectorResult:
        """Execute a connector query."""
        raise NotImplementedError

    async def health_check(self) -> bool:
        """Optional health check for the connector."""
        return True
