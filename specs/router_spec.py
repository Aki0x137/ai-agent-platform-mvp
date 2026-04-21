"""BDD Specs for ModelRouter - Test sensitivity classification"""
from specify import ObjectBehavior
from src.router import ModelRouter, PayloadClassifier, RoutingDecision


class PayloadClassifierSpec(ObjectBehavior):
    """Test payload sensitivity detection"""

    def _let(self):
        self._describe(PayloadClassifier)

    def it_detects_account_numbers(self):
        """Should detect account number patterns"""
        payload = {"account_id": "ACC-1234-5678-9012"}
        PayloadClassifier.is_sensitive(payload)._should_be(True)

    def it_detects_ssn(self):
        """Should detect SSN patterns"""
        payload = {"ssn": "123-45-6789"}
        PayloadClassifier.is_sensitive(payload)._should_be(True)

    def it_detects_credit_cards(self):
        """Should detect credit card patterns"""
        payload = {"card_number": "4532-1234-5678-9010"}
        PayloadClassifier.is_sensitive(payload)._should_be(True)

    def it_does_not_flag_benign_data(self):
        """Should not flag non-sensitive data"""
        payload = {"name": "John Doe", "company": "ACME"}
        PayloadClassifier.is_sensitive(payload)._should_be(False)

    def it_identifies_sensitive_fields(self):
        """Should identify which fields are sensitive"""
        payload = {
            "account_number": "123456",
            "balance": 1000.00,
            "ssn": "123-45-6789"
        }
        found = PayloadClassifier.identify_sensitive_fields(payload)
        found._should_have_length(2)  # account_number and ssn detected

    def it_redacts_sensitive_data(self):
        """Should replace sensitive values with [REDACTED]"""
        payload = {"ssn": "123-45-6789", "name": "John"}
        redacted = PayloadClassifier.redact_sensitive(payload)
        redacted["ssn"]._should_be_like("[REDACTED]")
        redacted["name"]._should_be_like("John")

    def it_redacts_nested_structures(self):
        """Should redact sensitive data in nested objects"""
        payload = {
            "user": {
                "name": "John",
                "ssn": "123-45-6789"
            },
            "accounts": [
                {"id": "123", "account_number": "ACC123"}
            ]
        }
        redacted = PayloadClassifier.redact_sensitive(payload)
        redacted["user"]["ssn"]._should_be_like("[REDACTED]")
        redacted["accounts"][0]["account_number"]._should_be_like("[REDACTED]")


class ModelRouterSpec(ObjectBehavior):
    """Test model routing decisions"""

    def _let(self):
        self._describe(ModelRouter)
        self._be_constructed_with(local_model="mistral")
        self.__router = self._get_subject()

    def it_routes_sensitive_policy_to_local(self):
        """Agents with 'sensitive' policy should route to local"""
        payload = {"query": "select * from accounts"}
        decision = self.__router.route(
            payload,
            model_policy="sensitive",
            tool_name="postgres.query"
        )
        decision._should_be(RoutingDecision.LOCAL)

    def it_routes_general_policy_to_cloud(self):
        """Agents with 'general' policy should route to cloud"""
        payload = {"task": "summarize this text"}
        decision = self.__router.route(
            payload,
            model_policy="general"
        )
        decision._should_be(RoutingDecision.CLOUD)

    def it_routes_hybrid_sensitive_payload_to_local(self):
        """Hybrid policy: sensitive payloads route to local"""
        payload = {"ssn": "123-45-6789", "name": "John"}
        decision = self.__router.route(
            payload,
            model_policy="hybrid"
        )
        decision._should_be(RoutingDecision.LOCAL)

    def it_routes_hybrid_benign_payload_redacted_to_cloud(self):
        """Hybrid policy: benign payloads route to cloud (redacted)"""
        payload = {"name": "John", "company": "ACME"}
        decision = self.__router.route(
            payload,
            model_policy="hybrid"
        )
        decision._should_be(RoutingDecision.REDACTED)

    def it_prepares_payload_for_cloud(self):
        """Should redact sensitive fields before sending to cloud"""
        payload = {"ssn": "123-45-6789", "name": "John"}
        prepared = self.__router.prepare_for_cloud(payload)
        prepared["ssn"]._should_be_like("[REDACTED]")
        prepared["name"]._should_be_like("John")

    def it_returns_local_endpoint_config(self):
        """Should return Ollama endpoint for local routing"""
        endpoint = self.__router.get_model_endpoint(RoutingDecision.LOCAL)
        endpoint["type"]._should_be_like("ollama")
        endpoint["model"]._should_be_like("mistral")
        endpoint["base_url"]._should_be_like("http://ollama:11434")

    def it_returns_cloud_endpoint_config(self):
        """Should return OpenAI endpoint for cloud routing"""
        endpoint = self.__router.get_model_endpoint(RoutingDecision.CLOUD)
        endpoint["type"]._should_be_like("openai")
        endpoint["base_url"]._should_contain("openai")
