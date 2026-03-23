from pydantic import BaseModel


class MetricsSummaryResponse(BaseModel):
    """Summary counters for dashboard."""

    total: int
    valid: int
    invalid: int
    success_rate: float
    reasons: dict[str, int]


class MetricsTimeseriesPoint(BaseModel):
    """Time bucket metrics entry."""

    bucket: str
    total: int
    valid: int
    invalid: int


class MetricsTimeseriesResponse(BaseModel):
    """Timeseries dataset for dashboard chart."""

    points: list[MetricsTimeseriesPoint]


class RecentValidationItem(BaseModel):
    """Recent processed lead item."""

    id: int
    lead_id: str
    contact_phone_raw: str
    normalized_phone: str | None
    status: str
    reason: str | None
    source: str
    processed_at: str
    client_ip: str | None = None
    ip_country: str | None = None
    assumed_dial_cc: str | None = None
    geo_mismatch: bool = False
    validation_confidence: str = "deterministic"
    default_cc_applied: bool = False


class RecentValidationsResponse(BaseModel):
    """Recent processed leads list."""

    items: list[RecentValidationItem]


class DeleteMetricsResponse(BaseModel):
    """Delete operation result."""

    deleted: int


class TopReasonItem(BaseModel):
    """Single bucket in top invalid reasons."""

    reason: str
    count: int


class AdvancedMetricsResponse(BaseModel):
    """Advanced dashboard analytics."""

    llm_share: float
    llm_success_rate: float
    deterministic_success_rate: float
    normalization_coverage: float
    invalid_share: float
    top_reasons: list[TopReasonItem]
    source_split: dict[str, int]
