import asyncio
import json
import logging
from typing import Protocol

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings

logger = logging.getLogger(__name__)

LLM_SYSTEM_PROMPT = """
You are a strict phone normalization assistant.
Your only task is to recover a single phone number to E.164 when possible.

Hard rules:
1) Output ONLY valid JSON object, no prose.
2) Never invent missing digits.
3) normalized_phone must be either:
   - E.164 format: plus sign + digits only, total 8..15 digits after plus
   - null if not confidently recoverable
4) Remove spaces, dashes, brackets, dots and other separators.
5) Fix obvious duplicated country code prefixes if unambiguous.
6) If input is ambiguous (multiple country interpretations) or nonsense, set normalized_phone to null and recoverable to false.
7) If number can be plausibly repaired without guessing, set recoverable to true.

Return keys exactly:
- normalized_phone
- recoverable
- reason
""".strip()


class LlmCorrectionResult(BaseModel):
    """Expected structured output from LLM correction."""

    normalized_phone: str | None
    recoverable: bool
    reason: str


class LlmCorrector(Protocol):
    """Port for LLM correction services."""

    async def attempt_fix(self, raw_phone: str) -> LlmCorrectionResult | None:
        """Attempt recovering phone string."""


class OpenAiLlmCorrector:
    """OpenAI-backed corrector using gpt-4o-mini."""

    def __init__(self) -> None:
        self._api_key = settings.openai_api_key
        self._model = settings.openai_model
        self._timeout = settings.openai_timeout_seconds

    async def attempt_fix(self, raw_phone: str) -> LlmCorrectionResult | None:
        """Attempt to recover raw phone with retries and strict JSON parsing."""
        if not self._api_key:
            return None

        schema_hint = {
            "normalized_phone": "E.164 string with leading plus, or null",
            "recoverable": "boolean",
            "reason": (
                "machine-readable reason, one of: "
                "already_e164, stripped_formatting, added_plus, fixed_duplicate_country_code, "
                "impossible_input, ambiguous_country, invalid_length, invalid_characters"
            ),
        }

        user_prompt = (
            "Normalize this phone candidate to E.164 if possible.\n"
            f"input_phone: {raw_phone}\n"
            f"output_schema: {json.dumps(schema_hint)}\n"
            "Important: return only JSON object."
        )

        payload = {
            "model": self._model,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": LLM_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            "temperature": 0,
        }

        for _ in range(3):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                        json=payload,
                    )
                    response.raise_for_status()

                content = response.json()["choices"][0]["message"]["content"]
                parsed = self._safe_json_parse(content)
                return LlmCorrectionResult.model_validate(parsed)
            except (httpx.HTTPError, KeyError, json.JSONDecodeError, ValidationError) as exc:
                logger.exception("LLM correction attempt failed: %s", exc)
                await asyncio.sleep(0.4)
        return None

    @staticmethod
    def _safe_json_parse(raw_content: str) -> dict[str, object]:
        """Parse JSON response and attempt a lightweight repair."""
        try:
            return json.loads(raw_content)
        except json.JSONDecodeError:
            repaired = raw_content.strip()
            if repaired.startswith("```"):
                repaired = repaired.strip("`")
                repaired = repaired.replace("json", "", 1).strip()
            return json.loads(repaired)
