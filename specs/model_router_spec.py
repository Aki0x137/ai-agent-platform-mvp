"""BDD Specs for ModelRouter - Test routing decisions"""
from specify import ObjectBehavior
from src.router import ModelRouter, PayloadClassifier, RoutingDecision


class ModelRouterSpec(ObjectBehavior):
    """Test model routing decisions"""

    def _let(self):
        self._describe(ModelRouter)
        self._be_constructed_with(local_model="mistral")

    def it_routes_sensitive_policy_to_local(self):
        """Agents with 'sensitive' policy should route to local"""
        payload = {"query": "select * from accounts"}
        self.route(
            payload,
            model_policy="sensitive",
            tool_name="postgres.query",
        )._should_be(RoutingDecision.LOCAL)

    def it_routes_general_policy_to_cloud(self):
        """Agents with 'general' policy should route to cloud"""
        payload = {"task": "summarize this text"}
        self.route(
            payload,
            model_policy="general",
        )._should_be(RoutingDecision.CLOUD)

    def it_routes_hybrid_sensitive_payload_to_local(self):
        """Hybrid policy: sensitive payloads route to local"""
        payload = {"ssn": "123-45-6789", "name": "John"}
        self.route(
            payload,
            model_policy="hybrid",
        )._should_be(RoutingDecision.LOCAL)

    def it_routes_hybrid_benign_payload_redacted_to_cloud(self):
        """Hybrid policy: benign payloads route to cloud (redacted)"""
        payload = {"name": "John", "company": "ACME"}
        self.route(
            payload,
            model_policy="hybrid",
        )._should_be(RoutingDecision.REDACTED)

    def it_prepares_payload_for_cloud(self):
        """Should redact sensitive fields before sending to cloud"""
        payload = {"ssn": "123-45-6789", "name": "John"}
        prepared = PayloadClassifier.redact_sensitive(payload)
        assert prepared["ssn"] == "[REDACTED]", f"Expected [REDACTED], got {prepared['ssn']}"
        assert prepared["name"] == "John", f"Expected John, got {prepared['name']}"

    def it_returns_local_endpoint_config(self):
        """Should return Ollama endpoint for local routing"""
        router = ModelRouter(local_model="mistral")
        endpoint = router.get_model_endpoint(RoutingDecision.LOCAL)
        assert endpoint["type"] == "ollama", f"Expected ollama, got {endpoint['type']}"
        assert endpoint["model"] == "mistral", f"Expected mistral, got {endpoint['model']}"

    def it_returns_cloud_endpoint_config(self):
        """Should return OpenAI endpoint for cloud routing"""
        router = ModelRouter(local_model="mistral")
        endpoint = router.get_model_endpoint(RoutingDecision.CLOUD)
        assert endpoint["type"] == "openai", f"Expected openai, got {endpoint['type']}"
        assert "openai" in endpoint["base_url"], f"Expected openai in base_url, got {endpoint['base_url']}"
