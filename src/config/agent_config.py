"""Agent configuration loader and validator."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.models import AgentConfig


def load_yaml_file(path: str | Path) -> dict[str, Any]:
    """Load YAML content from a file."""
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Agent config file not found: {path_obj}")

    with path_obj.open("r", encoding="utf-8") as handle:
        content = yaml.safe_load(handle)
        if content is None:
            raise ValueError(f"Agent config file is empty: {path_obj}")
        if not isinstance(content, dict):
            raise ValueError(f"Agent config file must contain a mapping at root: {path_obj}")
        return content


def load_agent_config(path: str = "config/reconciliation-agent.yaml") -> AgentConfig:
    """Load and validate the agent configuration from YAML."""
    raw = load_yaml_file(path)
    return AgentConfig(**raw)
