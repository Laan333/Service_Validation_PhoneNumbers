from datetime import UTC, datetime
import logging

from app.domain.enums import RejectionReason, ValidationStatus
from app.domain.models import LeadValidationRecord, ValidationDecision
from app.domain.phone_context import PhoneValidationContext
from app.repositories.lead_repository import LeadValidationRepository
from app.services.deterministic_validator import DeterministicPhoneValidator
from app.services.ip_geo import IpGeoService
from app.services.llm_correction import LlmCorrector

logger = logging.getLogger(__name__)


class PhoneValidationPipeline:
    """Main phone validation flow with deterministic + LLM fallback."""

    def __init__(
        self,
        validator: DeterministicPhoneValidator,
        llm_corrector: LlmCorrector,
        repository: LeadValidationRepository,
        ip_geo: IpGeoService,
    ) -> None:
        self._validator = validator
        self._llm_corrector = llm_corrector
        self._repository = repository
        self._ip_geo = ip_geo

    async def process(self, lead_id: str, raw_phone: str, *, client_ip: str | None = None) -> ValidationDecision:
        """Validate phone and persist the processing result."""
        logger.info("Lead %s: start validation for phone='%s' ip=%s", lead_id, raw_phone, client_ip or "-")
        geo_iso, default_applied = await self._ip_geo.resolve(client_ip)
        ctx = PhoneValidationContext(
            client_ip=client_ip,
            geo_country_iso=geo_iso,
            default_cc_applied=default_applied,
        )
        decision = self._validator.validate(raw_phone, ctx)
        logger.info(
            "Lead %s: deterministic decision status=%s recoverable=%s reason=%s geo=%s",
            lead_id,
            decision.status.value,
            decision.recoverable,
            decision.reason.value if decision.reason else "none",
            geo_iso,
        )
        if decision.status == ValidationStatus.VALID:
            await self._save(lead_id, raw_phone, decision)
            return decision

        if not decision.recoverable:
            await self._save(lead_id, raw_phone, decision)
            return decision

        llm_out = await self._llm_corrector.attempt_fix(raw_phone, geo_country_iso=geo_iso)
        if llm_out and llm_out.normalized_phone:
            logger.info(
                "Lead %s: llm proposed normalized_phone=%s reason=%s",
                lead_id,
                llm_out.normalized_phone,
                llm_out.reason,
            )
            recheck = self._validator.recheck_e164_only(llm_out.normalized_phone)
            if recheck.status == ValidationStatus.VALID:
                final = ValidationDecision(
                    status=ValidationStatus.VALID,
                    normalized_phone=recheck.normalized_phone,
                    reason=None,
                    recoverable=False,
                    source="llm",
                    assumed_dial_cc=recheck.assumed_dial_cc or None,
                    geo_mismatch=recheck.geo_mismatch,
                    confidence="llm",
                )
                self._validator.apply_context_stamp(final, ctx)
                await self._save(lead_id, raw_phone, final)
                return final
            logger.info("Lead %s: llm output failed post-validation.", lead_id)
        else:
            logger.info("Lead %s: llm did not return a valid candidate.", lead_id)

        us_fallback = self._validator.try_post_llm_us_nanp(raw_phone, ctx)
        if us_fallback:
            logger.info("Lead %s: post-llm NANP +1 fallback succeeded.", lead_id)
            self._validator.apply_context_stamp(us_fallback, ctx)
            await self._save(lead_id, raw_phone, us_fallback)
            return us_fallback

        fallback = ValidationDecision(
            status=ValidationStatus.INVALID,
            normalized_phone=None,
            reason=RejectionReason.NOT_RECOVERABLE,
            recoverable=False,
            source="llm",
            confidence="llm",
        )
        self._validator.apply_context_stamp(fallback, ctx)
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
            client_ip=decision.client_ip,
            ip_country=decision.ip_country,
            assumed_dial_cc=decision.assumed_dial_cc,
            geo_mismatch=decision.geo_mismatch,
            validation_confidence=decision.confidence,
            default_cc_applied=decision.default_cc_applied,
        )
        await self._repository.create(record)
