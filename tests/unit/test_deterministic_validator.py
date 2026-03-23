from app.domain.enums import RejectionReason, ValidationStatus
from app.services.deterministic_validator import DeterministicPhoneValidator


def test_ten_digit_number_marked_recoverable() -> None:
    validator = DeterministicPhoneValidator()

    decision = validator.validate("415 555 2671")

    assert decision.status == ValidationStatus.INVALID
    assert decision.normalized_phone is None
    assert decision.reason == RejectionReason.AMBIGUOUS_WITHOUT_COUNTRY
    assert decision.recoverable is True


def test_repeated_digits_rejected() -> None:
    validator = DeterministicPhoneValidator()

    decision = validator.validate("11111111111")

    assert decision.status == ValidationStatus.INVALID
    assert decision.reason == RejectionReason.REPEATED_DIGITS


def test_short_string_rejected() -> None:
    validator = DeterministicPhoneValidator()

    decision = validator.validate("123")

    assert decision.status == ValidationStatus.INVALID
    assert decision.reason == RejectionReason.TOO_SHORT
