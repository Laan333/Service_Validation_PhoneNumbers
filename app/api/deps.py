from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.repositories.lead_repository import LeadValidationRepository
from app.services.deterministic_validator import DeterministicPhoneValidator
from app.services.llm_correction import OpenAiLlmCorrector
from app.services.phone_pipeline import PhoneValidationPipeline


def get_repository(db_session: AsyncSession) -> LeadValidationRepository:
    """Build repository dependency."""
    return LeadValidationRepository(db_session)


def get_validator() -> DeterministicPhoneValidator:
    """Build validator dependency."""
    return DeterministicPhoneValidator()


def get_llm_corrector() -> OpenAiLlmCorrector:
    """Build LLM dependency."""
    return OpenAiLlmCorrector()


__all__ = ["get_db_session", "get_repository", "get_validator", "get_llm_corrector"]


def get_pipeline(
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    validator: Annotated[DeterministicPhoneValidator, Depends(get_validator)],
    llm_corrector: Annotated[OpenAiLlmCorrector, Depends(get_llm_corrector)],
) -> PhoneValidationPipeline:
    """Build application pipeline dependency."""
    repository = LeadValidationRepository(db_session)
    return PhoneValidationPipeline(validator=validator, llm_corrector=llm_corrector, repository=repository)


__all__.append("get_pipeline")


def verify_webhook_token(x_webhook_token: Annotated[str | None, Header()] = None) -> None:
    """Validate webhook token when protection is enabled."""
    if not settings.webhook_token:
        return
    if x_webhook_token != settings.webhook_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook token.")


__all__.append("verify_webhook_token")
