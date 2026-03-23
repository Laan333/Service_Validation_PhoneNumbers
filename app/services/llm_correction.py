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
6) US/Canada NANP: a bare 10-digit number (after removing formatting) that matches NXX-NXX-XXXX
   (area code and exchange do not start with 0 or 1) should become +1 followed by those 10 digits.
   This is a single unambiguous interpretation for North American leads — set recoverable to true and normalize.
7) Russian toll-free or mobile written with a leading trunk "8" (e.g. 8-800-… or 8-9XX-…) maps to +7
   by replacing that leading 8 with country code 7 (one leading 8 only).
8) If input is ambiguous (multiple plausible country interpretations, not covered above) or nonsense,
   set normalized_phone to null and recoverable to false.
9) If the number can be plausibly repaired per the rules above, set recoverable to true.

Examples (illustrative only; follow rules for any input):
- "3105559988" -> {"normalized_phone": "+13105559988", "recoverable": true, "reason": "added_plus"}
- "532-476-3000" -> {"normalized_phone": "+15324763000", "recoverable": true, "reason": "stripped_formatting"}
- "8-800-555-3535" -> {"normalized_phone": "+78005553535", "recoverable": true, "reason": "stripped_formatting"}
- "9161234567" -> {"normalized_phone": null, "recoverable": false, "reason": "ambiguous_country"}
  (could be US 916 area or another region — do not guess)

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

    async def attempt_fix(self, raw_phone: str, *, geo_country_iso: str | None = None) -> LlmCorrectionResult | None:
        """Attempt recovering phone string."""


class OpenAiLlmCorrector:
    """OpenAI-backed corrector using gpt-4o-mini."""

    def __init__(self) -> None:
        self._api_key = settings.openai_api_key
        self._model = settings.openai_model
        self._timeout = settings.openai_timeout_seconds

    async def attempt_fix(self, raw_phone: str, *, geo_country_iso: str | None = None) -> LlmCorrectionResult | None:
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

        geo_line = ""
        if geo_country_iso:
            geo_line = (
                f"visitor_geo_country_iso: {geo_country_iso}\n"
                "Use this as the default region when choosing a country calling code for local numbers "
                "(e.g. 10-digit numbers without a country prefix).\n"
            )
        user_prompt = (
            "Normalize this phone candidate to E.164 if possible.\n"
            f"{geo_line}"
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
