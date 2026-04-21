"""Model routing based on payload sensitivity"""
import json
import re
from typing import Any, Dict, Optional
from enum import Enum


class RoutingDecision(str, Enum):
    """Where to route LLM call"""
    LOCAL = "local"      # Ollama (on-prem)
    CLOUD = "cloud"      # Commercial API (OpenAI, Anthropic)
    REDACTED = "redacted"  # Redact sensitive data before sending to cloud


class PayloadClassifier:
    """Classifies payloads for sensitivity"""

    # Regex patterns for sensitive data
    SENSITIVE_PATTERNS = {
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "account_number": r"\baccount[\s_-]?(?:number|id|num|no)\b",
        "credit_card": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b",
        "pii_keywords": r"\b(ssn|social[\s_-]?security|tin|passport|license|dob|date[\s_-]?of[\s_-]?birth)\b",
        "financial_keywords": r"\b(balance|transaction|deposit|withdrawal|credit_limit|interest_rate|apr)\b",
    }

    @classmethod
    def is_sensitive(cls, data: Any) -> bool:
        """Check if data contains sensitive information"""
        text = cls._stringify(data)
        for pattern in cls.SENSITIVE_PATTERNS.values():
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    @classmethod
    def identify_sensitive_fields(cls, data: Any) -> Dict[str, list]:
        """Identify which fields contain sensitive data"""
        text = cls._stringify(data)
        found = {}

        for field_name, pattern in cls.SENSITIVE_PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                found[field_name] = matches[:3]  # Limit to 3 matches

        return found

    @classmethod
    def redact_sensitive(cls, data: Any) -> Any:
        """Redact sensitive information from data"""
        if isinstance(data, dict):
            redacted = {}
            for key, value in data.items():
                if cls._is_sensitive_key(key):
                    redacted[key] = "[REDACTED]"
                elif isinstance(value, (dict, list)):
                    redacted[key] = cls.redact_sensitive(value)
                else:
                    redacted[key] = value
            return redacted

        if isinstance(data, list):
            return [cls.redact_sensitive(item) for item in data]

        if isinstance(data, str):
            # Redact patterns in string
            result = data
            for pattern in cls.SENSITIVE_PATTERNS.values():
                result = re.sub(pattern, "[REDACTED]", result, flags=re.IGNORECASE)
            return result

        return data

    @classmethod
    def _stringify(cls, data: Any) -> str:
        """Convert data to string for pattern matching"""
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            return json.dumps(data)
        if isinstance(data, (list, tuple)):
            return json.dumps(data)
        return str(data)

    @classmethod
    def _is_sensitive_key(cls, key: str) -> bool:
        """Check if a key name indicates sensitive data"""
        sensitive_keys = {
            "ssn", "account", "password", "token", "secret", "api_key",
            "credit_card", "card_number", "cvv", "pin", "routing",
            "tin", "passport", "license", "dob", "date_of_birth",
            "pii", "sensitive"
        }
        return any(sk in key.lower() for sk in sensitive_keys)


class ModelRouter:
    """Routes LLM calls based on model policy and payload sensitivity"""

    def __init__(self, local_model: str = "mistral", default_policy: str = "hybrid"):
        self.local_model = local_model
        self.default_policy = default_policy
        self.classifier = PayloadClassifier()

    def route(
        self,
        payload: Any,
        model_policy: str = None,
        tool_name: Optional[str] = None,
    ) -> RoutingDecision:
        """
        Route an LLM call based on payload and policy.

        Args:
            payload: The data/context to be sent to LLM
            model_policy: Agent's model policy (sensitive|general|hybrid)
            tool_name: Name of tool being called (for context)

        Returns:
            RoutingDecision: Where to route the call
        """
        policy = model_policy or self.default_policy

        if policy == "sensitive":
            return RoutingDecision.LOCAL

        if policy == "general":
            return RoutingDecision.CLOUD

        # HYBRID: Per-tool-call routing based on payload
        if self._is_sensitive_payload(payload):
            return RoutingDecision.LOCAL
        else:
            return RoutingDecision.REDACTED  # Redact before sending to cloud

    def _is_sensitive_payload(self, payload: Any) -> bool:
        """Check if payload is sensitive"""
        return self.classifier.is_sensitive(payload)

    def prepare_for_cloud(self, payload: Any) -> Any:
        """
        Prepare payload for cloud API by redacting sensitive info.
        """
        return self.classifier.redact_sensitive(payload)

    def get_model_endpoint(self, routing_decision: RoutingDecision) -> Dict[str, Any]:
        """Get the endpoint config for the routing decision"""
        if routing_decision == RoutingDecision.LOCAL:
            return {
                "type": "ollama",
                "model": self.local_model,
                "base_url": "http://ollama:11434",
                "timeout": 120,
            }
        else:  # CLOUD or REDACTED
            return {
                "type": "openai",
                "model": "gpt-3.5-turbo",
                "base_url": "https://api.openai.com/v1",
                "timeout": 60,
            }

    def get_routing_info(
        self,
        payload: Any,
        model_policy: str,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get detailed routing information"""
        decision = self.route(payload, model_policy, tool_name)
        sensitive_fields = self.classifier.identify_sensitive_fields(payload)

        return {
            "routing_decision": decision.value,
            "model_policy": model_policy,
            "tool_name": tool_name,
            "payload_is_sensitive": bool(sensitive_fields),
            "sensitive_fields_detected": list(sensitive_fields.keys()),
            "endpoint": self.get_model_endpoint(decision),
        }
