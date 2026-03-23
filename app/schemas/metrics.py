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


class RecentValidationsResponse(BaseModel):
    """Recent processed leads list."""

    items: list[RecentValidationItem]


class DeleteMetricsResponse(BaseModel):
    """Delete operation result."""

    deleted: int


class AdvancedMetricsResponse(BaseModel):
    """Advanced dashboard analytics."""

    llm_share: float
    llm_success_rate: float
    deterministic_success_rate: float
    normalization_coverage: float
    invalid_share: float
    top_reasons: list[dict[str, int]]
    source_split: dict[str, int]
