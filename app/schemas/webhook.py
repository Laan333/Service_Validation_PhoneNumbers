from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import ValidationStatus


class CrmLeadPayload(BaseModel):
    """Incoming CRM lead payload."""

    id: str = Field(alias="ID")
    title: str = Field(default="", alias="TITLE")
    contact_phone: str = Field(default="", alias="CONTACT_PHONE")
    date_create: datetime | None = Field(default=None, alias="DATE_CREATE")


class WebhookValidationResponse(BaseModel):
    """Webhook response payload returned to CRM."""

    lead_id: str
    status: ValidationStatus
    normalized_phone: str | None = None
    reason: str | None = None
    source: str
