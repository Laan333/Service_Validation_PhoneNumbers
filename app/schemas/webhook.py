from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import ValidationStatus


class CrmLeadPayload(BaseModel):
    """Bitrix24-style CRM lead body (same shape as ``mock.json``).

    Validation uses ``ID`` and ``CONTACT_PHONE``; other fields are accepted for parity with real webhooks.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str = Field(alias="ID")
    title: str = Field(default="", alias="TITLE")
    stage_id: str | None = Field(default=None, alias="STAGE_ID")
    currency_id: str | None = Field(default=None, alias="CURRENCY_ID")
    contact_id: str | None = Field(default=None, alias="CONTACT_ID")
    contact_name: str | None = Field(default=None, alias="CONTACT_NAME")
    contact_email: str | None = Field(default=None, alias="CONTACT_EMAIL")
    contact_phone: str | None = Field(default=None, alias="CONTACT_PHONE")
    source_id: str | None = Field(default=None, alias="SOURCE_ID")
    comments: str | None = Field(default=None, alias="COMMENTS")
    utm_source: str | None = Field(default=None, alias="UTM_SOURCE")
    utm_medium: str | None = Field(default=None, alias="UTM_MEDIUM")
    utm_campaign: str | None = Field(default=None, alias="UTM_CAMPAIGN")
    utm_content: str | None = Field(default=None, alias="UTM_CONTENT")
    date_create: datetime | None = Field(default=None, alias="DATE_CREATE")

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id(cls, value: object) -> str:
        """Allow numeric IDs from CRM JSON."""
        if value is None:
            raise ValueError("ID is required")
        return str(value).strip()

    @field_validator("contact_phone", mode="before")
    @classmethod
    def normalize_phone(cls, value: object) -> str | None:
        """Normalize empty or whitespace-only phone to None."""
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None


class WebhookValidationResponse(BaseModel):
    """Webhook response payload returned to CRM."""

    lead_id: str
    status: ValidationStatus
    normalized_phone: str | None = None
    reason: str | None = None
    source: str
