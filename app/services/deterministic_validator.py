import logging
import re
from collections.abc import Iterable

from app.domain.enums import RejectionReason, ValidationStatus
from app.domain.models import ValidationDecision

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

        ru_domestic = self._normalize_russian_trunk_eight(digits_only)
        if ru_domestic is not None:
            return ValidationDecision(ValidationStatus.VALID, f"+{ru_domestic}", None)

        if cleaned.startswith("+"):
            normalized = f"+{digits_only}"
            if self._has_known_country_code(digits_only):
                return ValidationDecision(ValidationStatus.VALID, normalized, None)
            return ValidationDecision(ValidationStatus.INVALID, None, RejectionReason.UNKNOWN_COUNTRY_CODE, recoverable=True)

        if len(digits_only) == 10:
            if self._is_sequential_digit_run(digits_only):
                return ValidationDecision(
                    ValidationStatus.INVALID,
                    None,
                    RejectionReason.AMBIGUOUS_WITHOUT_COUNTRY,
                    recoverable=True,
                )
            if self._is_nanp_ten_digits(digits_only):
                return ValidationDecision(ValidationStatus.VALID, f"+1{digits_only}", None)
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

    def try_post_llm_us_nanp(self, raw_phone: str) -> ValidationDecision | None:
        """If input is 10-digit NANP (and not a sequential fake), normalize to +1.

        Used after LLM fails so obvious US local numbers still recover.
        """
        if not raw_phone or not raw_phone.strip():
            return None
        cleaned = self._strip_to_candidate(raw_phone)
        digits_only = re.sub(r"\D", "", cleaned)
        if len(digits_only) != 10:
            return None
        if self._is_sequential_digit_run(digits_only):
            return None
        if not self._is_nanp_ten_digits(digits_only):
            return None
        candidate = f"+1{digits_only}"
        recheck = self.validate(candidate)
        if recheck.status == ValidationStatus.VALID:
            return ValidationDecision(
                ValidationStatus.VALID,
                recheck.normalized_phone,
                None,
                recoverable=False,
                source="deterministic",
            )
        return None

    @staticmethod
    def _strip_to_candidate(raw_phone: str) -> str:
        return raw_phone.strip().replace(" ", "").replace("(", "").replace(")", "").replace("-", "")

    def _has_known_country_code(self, digits: str) -> bool:
        prefixes: Iterable[str] = (digits[:1], digits[:2], digits[:3])
        return any(prefix in KNOWN_COUNTRY_CODES for prefix in prefixes)

    @staticmethod
    def _is_nanp_ten_digits(digits: str) -> bool:
        """NANP national number: NXX-NXX-XXXX (N in 2–9 for NPA and exchange first digit)."""
        if len(digits) != 10 or not digits.isdigit():
            return False
        if digits[0] in "01" or digits[3] in "01":
            return False
        return True

    @staticmethod
    def _is_sequential_digit_run(digits: str) -> bool:
        """Detect 0123456789 / 9876543210 style fake inputs."""
        if len(digits) != 10 or not digits.isdigit():
            return False
        values = [int(ch) for ch in digits]
        ascending = all(values[i + 1] - values[i] == 1 for i in range(9))
        descending = all(values[i] - values[i + 1] == 1 for i in range(9))
        return ascending or descending

    def _normalize_russian_trunk_eight(self, digits_only: str) -> str | None:
        """Domestic RU format: leading trunk 8 + mobile 9… or toll-free 800… → E.164 without +."""
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
