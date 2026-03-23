from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, delete, func, select
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
                "id": row.id,
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

    async def delete_by_id(self, record_id: int) -> int:
        """Delete one validation row by primary key."""
        stmt = delete(LeadValidationORM).where(LeadValidationORM.id == record_id)
        result = await self._db_session.execute(stmt)
        await self._db_session.commit()
        return int(result.rowcount or 0)

    async def delete_all(self) -> int:
        """Delete all validation rows."""
        stmt = delete(LeadValidationORM)
        result = await self._db_session.execute(stmt)
        await self._db_session.commit()
        return int(result.rowcount or 0)

    async def advanced(self) -> dict[str, object]:
        """Return advanced analytics for dashboard."""
        totals_stmt = select(
            func.count(LeadValidationORM.id).label("total"),
            func.sum(case((LeadValidationORM.status == "invalid", 1), else_=0)).label("invalid"),
            func.sum(case((LeadValidationORM.source == "llm", 1), else_=0)).label("llm_total"),
            func.sum(case(((LeadValidationORM.source == "llm") & (LeadValidationORM.status == "valid"), 1), else_=0)).label(
                "llm_valid"
            ),
            func.sum(
                case(((LeadValidationORM.source == "deterministic") & (LeadValidationORM.status == "valid"), 1), else_=0)
            ).label("det_valid"),
            func.sum(case((LeadValidationORM.source == "deterministic", 1), else_=0)).label("det_total"),
            func.sum(case((LeadValidationORM.normalized_phone.is_not(None), 1), else_=0)).label("normalized_total"),
        )
        totals = (await self._db_session.execute(totals_stmt)).one()

        reason_stmt = (
            select(LeadValidationORM.reason, func.count(LeadValidationORM.id).label("count"))
            .where(LeadValidationORM.reason.is_not(None))
            .group_by(LeadValidationORM.reason)
            .order_by(func.count(LeadValidationORM.id).desc())
            .limit(5)
        )
        reason_rows: Sequence[tuple[str | None, int]] = (await self._db_session.execute(reason_stmt)).all()
        top_reasons = [{"reason": str(reason or "unknown"), "count": int(count)} for reason, count in reason_rows]

        source_stmt = select(LeadValidationORM.source, func.count(LeadValidationORM.id)).group_by(LeadValidationORM.source)
        source_rows: Sequence[tuple[str, int]] = (await self._db_session.execute(source_stmt)).all()
        source_split = {source: int(count) for source, count in source_rows}

        total = int(totals.total or 0)
        invalid = int(totals.invalid or 0)
        llm_total = int(totals.llm_total or 0)
        llm_valid = int(totals.llm_valid or 0)
        det_total = int(totals.det_total or 0)
        det_valid = int(totals.det_valid or 0)
        normalized_total = int(totals.normalized_total or 0)

        return {
            "llm_share": round((llm_total / total) if total else 0.0, 4),
            "llm_success_rate": round((llm_valid / llm_total) if llm_total else 0.0, 4),
            "deterministic_success_rate": round((det_valid / det_total) if det_total else 0.0, 4),
            "normalization_coverage": round((normalized_total / total) if total else 0.0, 4),
            "invalid_share": round((invalid / total) if total else 0.0, 4),
            "top_reasons": top_reasons,
            "source_split": source_split,
        }
