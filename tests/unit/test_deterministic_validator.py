from app.domain.enums import RejectionReason, ValidationStatus
from app.domain.phone_context import PhoneValidationContext
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
    ctx_us = PhoneValidationContext(None, "US", True)
    fb = validator.try_post_llm_us_nanp("3105559988", ctx_us)
    assert fb is not None
    assert fb.normalized_phone == "+13105559988"
    assert fb.status == ValidationStatus.VALID

    assert validator.try_post_llm_us_nanp("9876543210", ctx_us) is None
    assert validator.try_post_llm_us_nanp("9161234567", ctx_us) is None
    ctx_mx = PhoneValidationContext(None, "MX", False)
    assert validator.try_post_llm_us_nanp("3105559988", ctx_mx) is None


def test_mexico_ten_digit_uses_country_code_from_geo() -> None:
    validator = DeterministicPhoneValidator()
    ctx = PhoneValidationContext(None, "MX", False)
    decision = validator.validate("5512345678", ctx)
    assert decision.status == ValidationStatus.VALID
    assert decision.normalized_phone == "+525512345678"
    assert decision.assumed_dial_cc == "52"


def test_strip_erroneous_plus_one_before_italy() -> None:
    validator = DeterministicPhoneValidator()
    ctx = PhoneValidationContext(None, "US", True)
    decision = validator.validate("+1393792497015", ctx)
    assert decision.status == ValidationStatus.VALID
    assert decision.normalized_phone == "+393792497015"
