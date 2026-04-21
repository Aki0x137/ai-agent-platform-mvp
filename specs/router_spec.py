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
        self.is_sensitive(payload)._should_be(True)

    def it_detects_ssn(self):
        """Should detect SSN patterns"""
        payload = {"ssn": "123-45-6789"}
        self.is_sensitive(payload)._should_be(True)

    def it_detects_credit_cards(self):
        """Should detect credit card patterns"""
        payload = {"card_number": "4532-1234-5678-9010"}
        self.is_sensitive(payload)._should_be(True)

    def it_does_not_flag_benign_data(self):
        """Should not flag non-sensitive data"""
        payload = {"name": "John Doe", "company": "ACME"}
        self.is_sensitive(payload)._should_be(False)

    def it_identifies_sensitive_fields(self):
        """Should identify which fields are sensitive"""
        payload = {
            "account_number": "123456",
            "balance": 1000.00,
            "ssn": "123-45-6789"
        }
        found = PayloadClassifier.identify_sensitive_fields(payload)
        assert len(found) >= 2, f"Expected >=2 sensitive fields, got {len(found)}: {list(found.keys())}"

    def it_redacts_sensitive_data(self):
        """Should replace sensitive values with [REDACTED]"""
        payload = {"ssn": "123-45-6789", "name": "John"}
        redacted = PayloadClassifier.redact_sensitive(payload)
        assert redacted["ssn"] == "[REDACTED]", f"Expected [REDACTED], got {redacted['ssn']}"
        assert redacted["name"] == "John", f"Expected John, got {redacted['name']}"

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
        assert redacted["user"]["ssn"] == "[REDACTED]", f"Expected [REDACTED], got {redacted['user']['ssn']}"
        assert redacted["accounts"][0]["account_number"] == "[REDACTED]", \
            f"Expected [REDACTED], got {redacted['accounts'][0]['account_number']}"
