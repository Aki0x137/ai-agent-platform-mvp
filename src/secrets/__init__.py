"""Secrets and environment management"""
import os
from typing import Any, Dict, Optional
from dataclasses import dataclass
from pathlib import Path

import dotenv


@dataclass
class SecretManager:
    """Manages secrets from environment and Vault"""

    vault_addr: Optional[str] = None
    vault_token: Optional[str] = None
    env_file: Optional[Path] = None

    def __post_init__(self):
        """Load environment"""
        if self.env_file and self.env_file.exists():
            dotenv.load_dotenv(self.env_file)
        elif Path(".env").exists():
            dotenv.load_dotenv(".env")

        self.vault_addr = os.getenv("VAULT_ADDR", self.vault_addr)
        self.vault_token = os.getenv("VAULT_TOKEN", self.vault_token)

    def resolve(self, reference: str) -> str:
        """
        Resolve a secret reference.

        Formats:
        - {{env:VAR_NAME}} -> read from environment
        - {{vault:path/to/secret}} -> read from Vault (mocked for MVP)
        - plain string -> return as-is
        """
        if reference.startswith("{{env:") and reference.endswith("}}"):
            var_name = reference[6:-2]
            value = os.getenv(var_name)
            if value is None:
                raise ValueError(f"Environment variable '{var_name}' not found")
            return value

        if reference.startswith("{{vault:") and reference.endswith("}}"):
            vault_path = reference[8:-2]
            return self._resolve_vault(vault_path)

        return reference

    def _resolve_vault(self, path: str) -> str:
        """
        Resolve secret from Vault.
        For MVP, this is mocked and reads from environment.
        """
        # Map common vault paths to env vars for MVP
        vault_path_to_env = {
            "core_banking_host": "CORE_BANKING_HOST",
            "core_banking_ro_creds": "CORE_BANKING_RO_CREDS",
            "snowflake_account": "SNOWFLAKE_ACCOUNT",
            "openai_api_key": "OPENAI_API_KEY",
        }

        env_var = vault_path_to_env.get(path.split("/")[-1], path.upper())
        value = os.getenv(env_var)

        if value is None:
            raise ValueError(f"Vault secret at '{path}' (env: {env_var}) not found")

        return value

    def resolve_dict(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively resolve all secret references in a dictionary.
        """
        resolved = {}
        for key, value in obj.items():
            if isinstance(value, str):
                try:
                    resolved[key] = self.resolve(value)
                except ValueError:
                    resolved[key] = value
            elif isinstance(value, dict):
                resolved[key] = self.resolve_dict(value)
            elif isinstance(value, list):
                resolved[key] = [
                    self.resolve_dict(item) if isinstance(item, dict)
                    else self.resolve(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                resolved[key] = value
        return resolved

    @classmethod
    def from_env(cls) -> "SecretManager":
        """Create SecretManager from current environment"""
        return cls(
            vault_addr=os.getenv("VAULT_ADDR"),
            vault_token=os.getenv("VAULT_TOKEN"),
            env_file=Path(".env") if Path(".env").exists() else None
        )
