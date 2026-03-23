from app.domain.enums import RejectionReason, ValidationStatus
from app.services.deterministic_validator import DeterministicPhoneValidator


def test_ten_digit_nanp_us_normalized_deterministically() -> None:
    validator = DeterministicPhoneValidator()
    decision = validator.validate("415 555 2671")
    assert decision.status == ValidationStatus.VALID
    assert decision.normalized_phone == "+14155552671"
    assert decision.source == "deterministic"


def test_ten_digit_formatted_us_parentheses_normalized() -> None:
    validator = DeterministicPhoneValidator()
    decision = validator.validate("(714) 883-9188")
    assert decision.status == ValidationStatus.VALID
    assert decision.normalized_phone == "+17148839188"


def test_ten_digit_us_with_dashes_normalized() -> None:
    validator = DeterministicPhoneValidator()
    decision = validator.validate("532-476-3000")
    assert decision.status == ValidationStatus.VALID
    assert decision.normalized_phone == "+15324763000"


def test_russian_toll_free_trunk_eight() -> None:
    validator = DeterministicPhoneValidator()
    decision = validator.validate("8-800-555-3535")
    assert decision.status == ValidationStatus.VALID
    assert decision.normalized_phone == "+78005553535"


def test_russian_mobile_trunk_eight() -> None:
    validator = DeterministicPhoneValidator()
    decision = validator.validate("89161234567")
    assert decision.status == ValidationStatus.VALID
    assert decision.normalized_phone == "+79161234567"


def test_sequential_ten_digits_still_ambiguous_for_llm() -> None:
    validator = DeterministicPhoneValidator()
    decision = validator.validate("9876543210")
    assert decision.status == ValidationStatus.INVALID
    assert decision.reason == RejectionReason.AMBIGUOUS_WITHOUT_COUNTRY
    assert decision.recoverable is True


def test_nanp_invalid_exchange_stays_ambiguous() -> None:
    """9161234567: exchange 123 starts with 1 — not valid NANP; do not assume +1."""
    validator = DeterministicPhoneValidator()
    decision = validator.validate("9161234567")
    assert decision.status == ValidationStatus.INVALID
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


def test_post_llm_nanp_fallback() -> None:
    validator = DeterministicPhoneValidator()
    fb = validator.try_post_llm_us_nanp("3105559988")
    assert fb is not None
    assert fb.normalized_phone == "+13105559988"
    assert fb.status == ValidationStatus.VALID

    assert validator.try_post_llm_us_nanp("9876543210") is None
    assert validator.try_post_llm_us_nanp("9161234567") is None
