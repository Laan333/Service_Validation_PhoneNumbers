import logging
import re
from collections.abc import Iterable

from app.domain.enums import RejectionReason, ValidationStatus
from app.domain.models import ValidationDecision

logger = logging.getLogger(__name__)

KNOWN_COUNTRY_CODES: set[str] = {
    "1",
    "44",
    "52",
    "55",
    "57",
    "34",
    "33",
    "49",
    "39",
    "91",
}


class DeterministicPhoneValidator:
    """Deterministic phone validation and normalization service."""

    def validate(self, raw_phone: str) -> ValidationDecision:
        """Validate and normalize raw phone into E.164 when possible."""
        if not raw_phone or not raw_phone.strip():
            return ValidationDecision(ValidationStatus.INVALID, None, RejectionReason.EMPTY)

        cleaned = self._strip_to_candidate(raw_phone)
        digits_only = re.sub(r"\D", "", cleaned)

        if not digits_only:
            return ValidationDecision(ValidationStatus.INVALID, None, RejectionReason.NON_NUMERIC)
        if len(digits_only) < 8:
            return ValidationDecision(ValidationStatus.INVALID, None, RejectionReason.TOO_SHORT)
        if len(digits_only) > 15:
            return ValidationDecision(ValidationStatus.INVALID, None, RejectionReason.TOO_LONG)
        if len(set(digits_only)) == 1:
            return ValidationDecision(ValidationStatus.INVALID, None, RejectionReason.REPEATED_DIGITS)

        if cleaned.startswith("+"):
            normalized = f"+{digits_only}"
            if self._has_known_country_code(digits_only):
                return ValidationDecision(ValidationStatus.VALID, normalized, None)
            return ValidationDecision(ValidationStatus.INVALID, None, RejectionReason.UNKNOWN_COUNTRY_CODE, recoverable=True)

        if len(digits_only) == 10:
            return ValidationDecision(
                ValidationStatus.INVALID,
                None,
                RejectionReason.AMBIGUOUS_WITHOUT_COUNTRY,
                recoverable=True,
            )

        if len(digits_only) == 11 and digits_only.startswith("1"):
            normalized = f"+{digits_only}"
            return ValidationDecision(ValidationStatus.VALID, normalized, None)

        if self._has_known_country_code(digits_only):
            return ValidationDecision(ValidationStatus.VALID, f"+{digits_only}", None)

        return ValidationDecision(ValidationStatus.INVALID, None, RejectionReason.AMBIGUOUS_WITHOUT_COUNTRY, recoverable=True)

    @staticmethod
    def _strip_to_candidate(raw_phone: str) -> str:
        return raw_phone.strip().replace(" ", "").replace("(", "").replace(")", "").replace("-", "")

    def _has_known_country_code(self, digits: str) -> bool:
        prefixes: Iterable[str] = (digits[:1], digits[:2], digits[:3])
        return any(prefix in KNOWN_COUNTRY_CODES for prefix in prefixes)
