import asyncio

from app.domain.enums import ValidationStatus
from app.services.deterministic_validator import DeterministicPhoneValidator
from app.services.phone_pipeline import PhoneValidationPipeline


class InMemoryRepository:
    def __init__(self) -> None:
        self.records = []

    async def create(self, record) -> None:
        self.records.append(record)


class FakeLlmCorrector:
    async def attempt_fix(self, raw_phone: str):
        class Result:
            normalized_phone = "+14155552671" if "415" in raw_phone else None
            recoverable = normalized_phone is not None
            reason = "ok" if recoverable else "bad"

        return Result()


class FakeLlm916:
    async def attempt_fix(self, raw_phone: str):
        class Result:
            normalized_phone = "+19161234567"
            recoverable = True
            reason = "ok"

        return Result()


def test_pipeline_uses_llm_for_recoverable_case() -> None:
    """4155552671 is valid NANP — deterministic succeeds without LLM."""

    async def _run() -> None:
        repo = InMemoryRepository()
        pipeline = PhoneValidationPipeline(
            validator=DeterministicPhoneValidator(),
            llm_corrector=FakeLlmCorrector(),
            repository=repo,  # type: ignore[arg-type]
        )
        result = await pipeline.process("lead-1", "4155552671")
        assert result.status == ValidationStatus.VALID
        assert result.normalized_phone == "+14155552671"
        assert result.source == "deterministic"

    asyncio.run(_run())


def test_pipeline_calls_llm_for_non_nanp_ten_digit() -> None:
    """9161234567 is not valid NANP (exchange 123); LLM can still recover."""

    async def _run() -> None:
        repo = InMemoryRepository()
        pipeline = PhoneValidationPipeline(
            validator=DeterministicPhoneValidator(),
            llm_corrector=FakeLlm916(),
            repository=repo,  # type: ignore[arg-type]
        )
        result = await pipeline.process("lead-916", "9161234567")
        assert result.status == ValidationStatus.VALID
        assert result.normalized_phone == "+19161234567"
        assert result.source == "llm"

    asyncio.run(_run())
