from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import LeadValidationORM
from app.domain.models import LeadValidationRecord


class LeadValidationRepository:
    """Repository for lead validation records."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session

    async def create(self, record: LeadValidationRecord) -> None:
        """Persist validation record."""
        orm = LeadValidationORM(
            lead_id=record.lead_id,
            contact_phone_raw=record.contact_phone_raw,
            normalized_phone=record.normalized_phone,
            status=record.status.value,
            reason=record.reason,
            source=record.source,
            processed_at=record.processed_at,
        )
        self._db_session.add(orm)
        await self._db_session.commit()

    async def summary(self) -> dict[str, object]:
        """Return summary metrics for dashboard."""
        stmt = select(
            func.count(LeadValidationORM.id).label("total"),
            func.sum(case((LeadValidationORM.status == "valid", 1), else_=0)).label("valid"),
            func.sum(case((LeadValidationORM.status == "invalid", 1), else_=0)).label("invalid"),
        )
        row = (await self._db_session.execute(stmt)).one()

        reasons_stmt = (
            select(LeadValidationORM.reason, func.count(LeadValidationORM.id))
            .where(LeadValidationORM.reason.is_not(None))
            .group_by(LeadValidationORM.reason)
        )
        reasons_rows: Sequence[tuple[str | None, int]] = (await self._db_session.execute(reasons_stmt)).all()
        reasons = {reason or "unknown": count for reason, count in reasons_rows}

        total = int(row.total or 0)
        valid = int(row.valid or 0)
        invalid = int(row.invalid or 0)
        success_rate = (valid / total) if total else 0.0

        return {"total": total, "valid": valid, "invalid": invalid, "success_rate": round(success_rate, 4), "reasons": reasons}

    async def timeseries(self, days: int = 7) -> list[dict[str, object]]:
        """Return daily bucket metrics."""
        end = datetime.now(UTC)
        start = end - timedelta(days=days)
        bucket_expr = func.date_trunc("day", LeadValidationORM.processed_at)

        stmt = (
            select(
                bucket_expr.label("bucket"),
                func.count(LeadValidationORM.id).label("total"),
                func.sum(case((LeadValidationORM.status == "valid", 1), else_=0)).label("valid"),
                func.sum(case((LeadValidationORM.status == "invalid", 1), else_=0)).label("invalid"),
            )
            .where(LeadValidationORM.processed_at >= start)
            .group_by(bucket_expr)
            .order_by(bucket_expr.asc())
        )

        rows = (await self._db_session.execute(stmt)).all()
        return [
            {
                "bucket": row.bucket.isoformat() if row.bucket else "",
                "total": int(row.total or 0),
                "valid": int(row.valid or 0),
                "invalid": int(row.invalid or 0),
            }
            for row in rows
        ]

    async def recent(self, limit: int = 20) -> list[dict[str, object]]:
        """Return latest processed validations."""
        stmt = (
            select(LeadValidationORM)
            .order_by(LeadValidationORM.processed_at.desc())
            .limit(limit)
        )
        rows = (await self._db_session.execute(stmt)).scalars().all()
        return [
            {
                "lead_id": row.lead_id,
                "contact_phone_raw": row.contact_phone_raw,
                "normalized_phone": row.normalized_phone,
                "status": row.status,
                "reason": row.reason,
                "source": row.source,
                "processed_at": row.processed_at.isoformat() if row.processed_at else "",
            }
            for row in rows
        ]
