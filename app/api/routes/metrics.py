from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.repositories.lead_repository import LeadValidationRepository
from app.schemas.metrics import (
    MetricsSummaryResponse,
    MetricsTimeseriesPoint,
    MetricsTimeseriesResponse,
    DeleteMetricsResponse,
    AdvancedMetricsResponse,
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
    limit: int = Query(default=20, ge=1, le=100),
) -> RecentValidationsResponse:
    """Get latest processed validations."""
    repository = LeadValidationRepository(db_session)
    items = await repository.recent(limit=limit)
    mapped = [RecentValidationItem.model_validate(item) for item in items]
    return RecentValidationsResponse(items=mapped)


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
