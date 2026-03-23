from fastapi.testclient import TestClient

from app.api.deps import get_pipeline
from app.core.config import settings
from app.domain.enums import ValidationStatus
from app.domain.models import ValidationDecision
from app.main import app


class FakePipeline:
    async def process(self, lead_id: str, raw_phone: str) -> ValidationDecision:
        _ = lead_id, raw_phone
        return ValidationDecision(
            status=ValidationStatus.VALID,
            normalized_phone="+14155552671",
            reason=None,
            source="deterministic",
        )


def test_webhook_returns_validation_payload() -> None:
    app.dependency_overrides[get_pipeline] = lambda: FakePipeline()
    client = TestClient(app)

    response = client.post(
        "/api/v1/webhooks/crm/lead",
        json={"ID": "1", "TITLE": "Deal", "CONTACT_PHONE": "4155552671"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["lead_id"] == "1"
    assert body["status"] == "valid"
    assert body["normalized_phone"] == "+14155552671"

    app.dependency_overrides.clear()


def test_webhook_rejects_invalid_token_when_enabled() -> None:
    app.dependency_overrides[get_pipeline] = lambda: FakePipeline()
    previous = settings.webhook_token
    settings.webhook_token = "secret-token"
    client = TestClient(app)
    response = client.post("/api/v1/webhooks/crm/lead", json={"ID": "1", "CONTACT_PHONE": "4155552671"})
    settings.webhook_token = previous

    assert response.status_code == 401
    app.dependency_overrides.clear()
