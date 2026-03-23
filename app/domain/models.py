from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import RejectionReason, ValidationStatus


@dataclass(slots=True)
class ValidationDecision:
    """Domain value object for phone validation result."""

    status: ValidationStatus
    normalized_phone: str | None
    reason: RejectionReason | None
    recoverable: bool = False
    source: str = "deterministic"
    client_ip: str | None = None
    ip_country: str | None = None
    assumed_dial_cc: str | None = None
    geo_mismatch: bool = False
    confidence: str = "deterministic"
    default_cc_applied: bool = False


@dataclass(slots=True)
class LeadValidationRecord:
    """Persisted lead validation data."""

    lead_id: str
    contact_phone_raw: str
    normalized_phone: str | None
    status: ValidationStatus
    reason: str | None
    source: str
    processed_at: datetime
    client_ip: str | None = None
    ip_country: str | None = None
    assumed_dial_cc: str | None = None
    geo_mismatch: bool = False
    validation_confidence: str = "deterministic"
    default_cc_applied: bool = False
