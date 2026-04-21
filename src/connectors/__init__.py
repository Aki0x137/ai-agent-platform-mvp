"""Connector registry and shared models for FinAgent."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Type

from .base import Connector, ConnectorResult
from .postgres_connector import PostgreSQLConnector
from .rest_connector import RestApiConnector
from .inmemory_connector import InMemoryConnector
from .sandbox_connector import SandboxConnector
from .logs_connector import LogsConnector

ConnectorFactory = Callable[[str, dict[str, Any]], Connector]


class ConnectorRegistry:
    """Registry for connector classes."""

    _registry: Dict[str, Type[Connector]] = {}

    @classmethod
    def register(cls, connector_type: str, connector_class: Type[Connector]) -> None:
        cls._registry[connector_type] = connector_class

    @classmethod
    def get(cls, connector_type: str) -> Optional[Type[Connector]]:
        return cls._registry.get(connector_type)

    @classmethod
    def create(cls, connector_type: str, name: str, config: dict[str, Any]) -> Connector:
        connector_class = cls.get(connector_type)
        if not connector_class:
            raise ValueError(f"Connector type not registered: {connector_type}")
        return connector_class(name=name, config=config)

    @classmethod
    def registered_types(cls) -> list[str]:
        return list(cls._registry.keys())


# Register all built-in connector implementations
ConnectorRegistry.register("postgresql", PostgreSQLConnector)
ConnectorRegistry.register("rest_api", RestApiConnector)
ConnectorRegistry.register("inmemory", InMemoryConnector)
ConnectorRegistry.register("sandbox", SandboxConnector)
ConnectorRegistry.register("logs", LogsConnector)


__all__ = [
    "Connector",
    "ConnectorResult",
    "ConnectorRegistry",
    "PostgreSQLConnector",
    "RestApiConnector",
    "InMemoryConnector",
    "SandboxConnector",
    "LogsConnector",
]
