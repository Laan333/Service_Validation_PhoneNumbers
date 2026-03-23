from enum import StrEnum


class ValidationStatus(StrEnum):
    """Validation result status."""

    VALID = "valid"
    INVALID = "invalid"


class RejectionReason(StrEnum):
    """Known rejection reasons."""

    EMPTY = "empty_input"
    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"
    NON_NUMERIC = "non_numeric"
    REPEATED_DIGITS = "repeated_digits"
    UNKNOWN_COUNTRY_CODE = "unknown_country_code"
    AMBIGUOUS_WITHOUT_COUNTRY = "ambiguous_without_country"
    IMPOSSIBLE_PATTERN = "impossible_pattern"
    LLM_NOT_CONFIGURED = "llm_not_configured"
    LLM_FAILED = "llm_failed"
    NOT_RECOVERABLE = "not_recoverable"
