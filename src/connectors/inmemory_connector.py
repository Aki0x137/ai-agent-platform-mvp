"""InMemory connector for FinAgent — serves fixture data from in-process dicts."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .base import Connector, ConnectorResult


class InMemoryConnector(Connector):
    """
    Serves fixture data held in-process.

    Construction:
      - If ``data`` kwarg is provided, use it directly.
      - Otherwise load from ``config['source']`` path (JSON file).
    """

    def __init__(self, name: str, config: dict[str, Any], data: Any = None) -> None:
        super().__init__(name, config)
        self._data = data

    @property
    def connector_type(self) -> str:
        return "inmemory"

    def _ensure_loaded(self) -> None:
        """Load from file the first time if data was not injected."""
        if self._data is not None:
            return
        source = self.config.get("source")
        if not source:
            return
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"InMemoryConnector: source file not found: {path}")
        self._data = json.loads(path.read_text(encoding="utf-8"))

    async def query(self, request: dict[str, Any]) -> ConnectorResult:
        """
        Retrieve in-memory data.

        Request keys:
          operation (str): 'get' (default).
          key (str): Optional top-level key to return instead of full dataset.
        """
        start = time.monotonic()
        try:
            self._ensure_loaded()
        except Exception as exc:
            return ConnectorResult(
                success=False,
                error=str(exc),
                connector_name=self.name,
            )

        if self._data is None:
            return ConnectorResult(
                success=False,
                error="InMemoryConnector has no data loaded",
                connector_name=self.name,
            )

        key = request.get("key")
        if key is not None:
            if not isinstance(self._data, dict) or key not in self._data:
                elapsed = int((time.monotonic() - start) * 1000)
                return ConnectorResult(
                    success=False,
                    error=f"Key '{key}' not found in dataset",
                    execution_time_ms=elapsed,
                    connector_name=self.name,
                )
            payload = self._data[key]
        else:
            payload = self._data

        elapsed = int((time.monotonic() - start) * 1000)
        return ConnectorResult(
            success=True,
            data=[payload],
            execution_time_ms=elapsed,
            connector_name=self.name,
        )

    async def health_check(self) -> bool:
        try:
            self._ensure_loaded()
            return self._data is not None
        except Exception:
            return False
