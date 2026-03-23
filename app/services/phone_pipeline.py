from datetime import UTC, datetime
import logging

from app.domain.enums import RejectionReason, ValidationStatus
from app.domain.models import LeadValidationRecord, ValidationDecision
from app.repositories.lead_repository import LeadValidationRepository
from app.services.deterministic_validator import DeterministicPhoneValidator
from app.services.llm_correction import LlmCorrector

logger = logging.getLogger(__name__)


class PhoneValidationPipeline:
    """Main phone validation flow with deterministic + LLM fallback."""

    def __init__(
        self,
        validator: DeterministicPhoneValidator,
        llm_corrector: LlmCorrector,
        repository: LeadValidationRepository,
    ) -> None:
        self._validator = validator
        self._llm_corrector = llm_corrector
        self._repository = repository

    async def process(self, lead_id: str, raw_phone: str) -> ValidationDecision:
        """Validate phone and persist the processing result."""
        logger.info("Lead %s: start validation for phone='%s'", lead_id, raw_phone)
        decision = self._validator.validate(raw_phone)
        logger.info(
            "Lead %s: deterministic decision status=%s recoverable=%s reason=%s",
            lead_id,
            decision.status.value,
            decision.recoverable,
            decision.reason.value if decision.reason else "none",
        )
        if decision.status == ValidationStatus.VALID:
            await self._save(lead_id, raw_phone, decision)
            return decision

        if not decision.recoverable:
            await self._save(lead_id, raw_phone, decision)
            return decision

        llm_out = await self._llm_corrector.attempt_fix(raw_phone)
        if llm_out and llm_out.normalized_phone:
            logger.info(
                "Lead %s: llm proposed normalized_phone=%s reason=%s",
                lead_id,
                llm_out.normalized_phone,
                llm_out.reason,
            )
            recheck = self._validator.validate(llm_out.normalized_phone)
            if recheck.status == ValidationStatus.VALID:
                final = ValidationDecision(
                    status=ValidationStatus.VALID,
                    normalized_phone=recheck.normalized_phone,
                    reason=None,
                    recoverable=False,
                    source="llm",
                )
                await self._save(lead_id, raw_phone, final)
                return final
            logger.info("Lead %s: llm output failed post-validation.", lead_id)
        else:
            logger.info("Lead %s: llm did not return a valid candidate.", lead_id)

        fallback = ValidationDecision(
            status=ValidationStatus.INVALID,
            normalized_phone=None,
            reason=RejectionReason.NOT_RECOVERABLE,
            recoverable=False,
            source="llm",
        )
        await self._save(lead_id, raw_phone, fallback)
        return fallback

    async def _save(self, lead_id: str, raw_phone: str, decision: ValidationDecision) -> None:
        record = LeadValidationRecord(
            lead_id=lead_id,
            contact_phone_raw=raw_phone,
            normalized_phone=decision.normalized_phone,
            status=decision.status,
            reason=decision.reason.value if decision.reason else None,
            source=decision.source,
            processed_at=datetime.now(UTC),
        )
        await self._repository.create(record)
