from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.repositories.lead_repository import LeadValidationRepository
from app.schemas.metrics import (
    AdvancedMetricsResponse,
    DeleteMetricsResponse,
    InvalidReasonCountItem,
    InvalidReasonsChartResponse,
    LlmTimeseriesPoint,
    LlmTimeseriesResponse,
    MetricsSummaryResponse,
    MetricsTimeseriesPoint,
    MetricsTimeseriesResponse,
    MismatchByCcItem,
    MismatchByCcResponse,
    RecentValidationItem,
    RecentValidationsResponse,
)

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@router.get("/summary", response_model=MetricsSummaryResponse)
async def get_summary(
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MetricsSummaryResponse:
    """Get aggregate validation metrics."""
    repository = LeadValidationRepository(db_session)
    summary = await repository.summary()
    return MetricsSummaryResponse.model_validate(summary)


@router.get("/timeseries", response_model=MetricsTimeseriesResponse)
async def get_timeseries(
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    days: int = Query(default=7, ge=1, le=90),
) -> MetricsTimeseriesResponse:
    """Get daily timeseries metrics."""
    repository = LeadValidationRepository(db_session)
    points = await repository.timeseries(days=days)
    mapped = [MetricsTimeseriesPoint.model_validate(point) for point in points]
    return MetricsTimeseriesResponse(points=mapped)


@router.get("/recent", response_model=RecentValidationsResponse)
async def get_recent(
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = Query(default=20, ge=1, le=500),
    geo_mismatch_only: bool = Query(
        default=False,
        description="If true, return only rows where phone CC disagrees with visitor geo.",
    ),
    confidence: Literal["deterministic", "llm"] | None = Query(
        default=None,
        description="Filter by validation_confidence (same values as Source column).",
    ),
    status: Literal["valid", "invalid"] | None = Query(default=None, description="Filter by validation outcome."),
) -> RecentValidationsResponse:
    """Get latest processed validations."""
    repository = LeadValidationRepository(db_session)
    items = await repository.recent(
        limit=limit,
        geo_mismatch_only=True if geo_mismatch_only else None,
        confidence=confidence,
        status_filter=status,
    )
    mapped = [RecentValidationItem.model_validate(item) for item in items]
    return RecentValidationsResponse(items=mapped)


@router.get("/chart/mismatch-by-cc", response_model=MismatchByCcResponse)
async def get_chart_mismatch_by_cc(
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = Query(default=24, ge=1, le=64),
    days: int | None = Query(default=None, ge=1, le=90, description="Restrict to rows processed in the last N days."),
) -> MismatchByCcResponse:
    """Geo-mismatch rows grouped by assumed E.164 country calling code."""
    repository = LeadValidationRepository(db_session)
    rows = await repository.mismatch_counts_by_dial_cc(limit=limit, days=days)
    items = [MismatchByCcItem.model_validate(r) for r in rows]
    return MismatchByCcResponse(items=items)


@router.get("/chart/llm-timeseries", response_model=LlmTimeseriesResponse)
async def get_chart_llm_timeseries(
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    days: int = Query(default=7, ge=1, le=90),
) -> LlmTimeseriesResponse:
    """Daily count of validations by pipeline source (deterministic vs llm)."""
    repository = LeadValidationRepository(db_session)
    rows = await repository.timeseries_llm_usage(days=days)
    points = [LlmTimeseriesPoint.model_validate(r) for r in rows]
    return LlmTimeseriesResponse(points=points)


@router.get("/chart/invalid-reasons", response_model=InvalidReasonsChartResponse)
async def get_chart_invalid_reasons(
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    days: int | None = Query(default=None, ge=1, le=90, description="Restrict to rows processed in the last N days."),
) -> InvalidReasonsChartResponse:
    """Invalid rows only: histogram of rejection reasons."""
    repository = LeadValidationRepository(db_session)
    rows = await repository.invalid_reason_distribution(days=days)
    items = [InvalidReasonCountItem.model_validate(r) for r in rows]
    return InvalidReasonsChartResponse(items=items)


@router.get("/advanced", response_model=AdvancedMetricsResponse)
async def get_advanced(
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdvancedMetricsResponse:
    """Get advanced analytics."""
    repository = LeadValidationRepository(db_session)
    advanced = await repository.advanced()
    return AdvancedMetricsResponse.model_validate(advanced)


@router.delete("/recent/{record_id}", response_model=DeleteMetricsResponse)
async def delete_recent_one(
    record_id: int,
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DeleteMetricsResponse:
    """Delete one processed validation by id."""
    repository = LeadValidationRepository(db_session)
    deleted = await repository.delete_by_id(record_id)
    if deleted == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found.")
    return DeleteMetricsResponse(deleted=deleted)


@router.delete("/recent", response_model=DeleteMetricsResponse)
async def delete_recent_all(
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DeleteMetricsResponse:
    """Delete all processed validations."""
    repository = LeadValidationRepository(db_session)
    deleted = await repository.delete_all()
    return DeleteMetricsResponse(deleted=deleted)
