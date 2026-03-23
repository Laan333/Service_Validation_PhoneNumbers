import logging
import re
from collections.abc import Iterable

from app.core.config import settings
from app.domain.enums import RejectionReason, ValidationStatus
from app.domain.models import ValidationDecision
from app.domain.phone_context import PhoneValidationContext
from app.services.phone_geo import dial_for_geo, strip_erroneous_leading_us_one

logger = logging.getLogger(__name__)

KNOWN_COUNTRY_CODES: set[str] = {
    "1",
    "7",
    "44",
    "52",
    "55",
    "57",
    "34",
    "33",
    "49",
    "39",
    "91",
    "61",
}

_NEUTRAL_CTX = PhoneValidationContext(client_ip=None, geo_country_iso="US", default_cc_applied=True)


class DeterministicPhoneValidator:
    """Deterministic phone validation and normalization service."""

    def validate(self, raw_phone: str, context: PhoneValidationContext | None = None) -> ValidationDecision:
        """Validate and normalize raw phone into E.164 when possible."""
        ctx = context or PhoneValidationContext(
            client_ip=None,
            geo_country_iso=settings.ip_geo_default_country.upper(),
            default_cc_applied=True,
        )
        decision = self._validate_impl(raw_phone, ctx)
        self._stamp_geo_meta(decision, ctx)
        return decision

    def _stamp_geo_meta(self, decision: ValidationDecision, ctx: PhoneValidationContext) -> None:
        decision.client_ip = ctx.client_ip
        decision.ip_country = ctx.geo_country_iso
        decision.default_cc_applied = ctx.default_cc_applied

    def apply_context_stamp(self, decision: ValidationDecision, ctx: PhoneValidationContext) -> None:
        """Attach client IP / geo fields (e.g. after LLM or fallback paths)."""
        self._stamp_geo_meta(decision, ctx)

    def recheck_e164_only(self, candidate: str) -> ValidationDecision:
        """Re-validate a candidate string without applying the original client geo stamp."""
        return self._validate_impl(candidate, _NEUTRAL_CTX)

    def _validate_impl(self, raw_phone: str, ctx: PhoneValidationContext) -> ValidationDecision:
        if not raw_phone or not raw_phone.strip():
            return ValidationDecision(ValidationStatus.INVALID, None, RejectionReason.EMPTY)

        cleaned = self._strip_to_candidate(raw_phone)
        digits_only = strip_erroneous_leading_us_one(re.sub(r"\D", "", cleaned))

        if not digits_only:
            return ValidationDecision(ValidationStatus.INVALID, None, RejectionReason.NON_NUMERIC)
        if len(digits_only) < 8:
            return ValidationDecision(ValidationStatus.INVALID, None, RejectionReason.TOO_SHORT)
        if len(digits_only) > 15:
            return ValidationDecision(ValidationStatus.INVALID, None, RejectionReason.TOO_LONG)
        if len(set(digits_only)) == 1:
            return ValidationDecision(ValidationStatus.INVALID, None, RejectionReason.REPEATED_DIGITS)

        ru_domestic = self._normalize_russian_trunk_eight(digits_only)
        if ru_domestic is not None:
            dec = ValidationDecision(ValidationStatus.VALID, f"+{ru_domestic}", None)
            dec.assumed_dial_cc = "7"
            dec.geo_mismatch = ctx.geo_country_iso not in ("RU", "BY", "KZ")
            return dec

        if cleaned.startswith("+"):
            normalized = f"+{digits_only}"
            if self._has_known_country_code(digits_only):
                dec = ValidationDecision(ValidationStatus.VALID, normalized, None)
                dec.assumed_dial_cc = self._infer_cc_from_digits(digits_only)
                return dec
            return ValidationDecision(ValidationStatus.INVALID, None, RejectionReason.UNKNOWN_COUNTRY_CODE, recoverable=True)

        if len(digits_only) == 10:
            return self._ten_digit_local(digits_only, ctx)

        if len(digits_only) == 11 and digits_only.startswith("1"):
            normalized = f"+{digits_only}"
            dec = ValidationDecision(ValidationStatus.VALID, normalized, None)
            dec.assumed_dial_cc = "1"
            return dec

        if self._has_known_country_code(digits_only):
            dec = ValidationDecision(ValidationStatus.VALID, f"+{digits_only}", None)
            dec.assumed_dial_cc = self._infer_cc_from_digits(digits_only)
            return dec

        return ValidationDecision(ValidationStatus.INVALID, None, RejectionReason.AMBIGUOUS_WITHOUT_COUNTRY, recoverable=True)

    def _ten_digit_local(self, digits_only: str, ctx: PhoneValidationContext) -> ValidationDecision:
        if self._is_sequential_digit_run(digits_only):
            return ValidationDecision(
                ValidationStatus.INVALID,
                None,
                RejectionReason.AMBIGUOUS_WITHOUT_COUNTRY,
                recoverable=True,
            )

        dial = dial_for_geo(ctx.geo_country_iso) or "1"

        if dial == "1":
            if self._is_nanp_ten_digits(digits_only):
                dec = ValidationDecision(ValidationStatus.VALID, f"+1{digits_only}", None)
                dec.assumed_dial_cc = "1"
                dec.geo_mismatch = False
                return dec
            return ValidationDecision(
                ValidationStatus.INVALID,
                None,
                RejectionReason.AMBIGUOUS_WITHOUT_COUNTRY,
                recoverable=True,
            )

        national = dial + digits_only
        if len(national) <= 15 and self._has_known_country_code(national):
            dec = ValidationDecision(ValidationStatus.VALID, f"+{national}", None)
            dec.assumed_dial_cc = dial
            dec.geo_mismatch = self._is_nanp_ten_digits(digits_only)
            return dec

        return ValidationDecision(
            ValidationStatus.INVALID,
            None,
            RejectionReason.AMBIGUOUS_WITHOUT_COUNTRY,
            recoverable=True,
        )

    def try_post_llm_us_nanp(self, raw_phone: str, ctx: PhoneValidationContext) -> ValidationDecision | None:
        """If geo allows US/CA default, recover 10-digit NANP after LLM failure."""
        if not self._allows_us_nanp_fallback(ctx):
            return None
        if not raw_phone or not raw_phone.strip():
            return None
        cleaned = self._strip_to_candidate(raw_phone)
        digits_only = strip_erroneous_leading_us_one(re.sub(r"\D", "", cleaned))
        if len(digits_only) != 10:
            return None
        if self._is_sequential_digit_run(digits_only):
            return None
        if not self._is_nanp_ten_digits(digits_only):
            return None
        candidate = f"+1{digits_only}"
        recheck = self._validate_impl(candidate, _NEUTRAL_CTX)
        if recheck.status == ValidationStatus.VALID:
            dec = ValidationDecision(
                ValidationStatus.VALID,
                recheck.normalized_phone,
                None,
                recoverable=False,
                source="deterministic",
                assumed_dial_cc="1",
                confidence="deterministic",
            )
            return dec
        return None

    @staticmethod
    def _allows_us_nanp_fallback(ctx: PhoneValidationContext) -> bool:
        if ctx.geo_country_iso in ("US", "CA"):
            return True
        if ctx.default_cc_applied and settings.ip_geo_default_country.upper() in ("US", "CA"):
            return True
        return False

    @staticmethod
    def _infer_cc_from_digits(digits: str) -> str:
        for length in (3, 2, 1):
            prefix = digits[:length]
            if prefix in KNOWN_COUNTRY_CODES:
                return prefix
        return ""

    @staticmethod
    def _strip_to_candidate(raw_phone: str) -> str:
        return raw_phone.strip().replace(" ", "").replace("(", "").replace(")", "").replace("-", "")

    def _has_known_country_code(self, digits: str) -> bool:
        prefixes: Iterable[str] = (digits[:1], digits[:2], digits[:3])
        return any(prefix in KNOWN_COUNTRY_CODES for prefix in prefixes)

    @staticmethod
    def _is_nanp_ten_digits(digits: str) -> bool:
        if len(digits) != 10 or not digits.isdigit():
            return False
        if digits[0] in "01" or digits[3] in "01":
            return False
        return True

    @staticmethod
    def _is_sequential_digit_run(digits: str) -> bool:
        if len(digits) != 10 or not digits.isdigit():
            return False
        values = [int(ch) for ch in digits]
        ascending = all(values[i + 1] - values[i] == 1 for i in range(9))
        descending = all(values[i] - values[i + 1] == 1 for i in range(9))
        return ascending or descending

    def _normalize_russian_trunk_eight(self, digits_only: str) -> str | None:
        if len(digits_only) != 11 or not digits_only.startswith("8"):
            return None
        if not (digits_only.startswith("89") or digits_only.startswith("880")):
            return None
        national = digits_only[1:]
        if len(national) != 10:
            return None
        inner = "7" + national
        if self._has_known_country_code(inner):
            return inner
        return None
