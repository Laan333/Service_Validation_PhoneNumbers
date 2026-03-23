from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, MetaData, String, func, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base for ORM models."""

    metadata = MetaData()


class LeadValidationORM(Base):
    """Stored validation record."""

    __tablename__ = "lead_validations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str] = mapped_column(String(128), index=True)
    contact_phone_raw: Mapped[str] = mapped_column(String(128))
    normalized_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    reason: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(32), default="deterministic")
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    client_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    ip_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    assumed_dial_cc: Mapped[str | None] = mapped_column(String(8), nullable=True)
    geo_mismatch: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    validation_confidence: Mapped[str] = mapped_column(String(32), nullable=False, server_default="deterministic")
    default_cc_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))


engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncSession:
    """Yield async database session."""
    async with SessionLocal() as session:
        yield session
