"""Normalize Bitrix-style CRM JSON (mock file + webhook bodies)."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _parse_fields_value(value: object) -> dict[str, Any] | None:
    """Parse Bitrix ``FIELDS`` when it is a dict or a JSON object string."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            logger.debug("FIELDS string is not valid JSON, skipping unwrap.")
            return None
        if isinstance(parsed, dict):
            return parsed
    return None


def unwrap_bitrix_lead_body(raw: dict[str, Any]) -> dict[str, Any]:
    """Unwrap Bitrix-style envelopes for a single lead.

    Handles ``{"FIELDS": {...}}`` and ``{"data": {"FIELDS": ...}}`` (dict or JSON string).
    Flat payloads with top-level ``ID`` / ``CONTACT_PHONE`` are returned unchanged.

    Returns:
        Flat dict suitable for :class:`~app.schemas.webhook.CrmLeadPayload`.
    """
    fields = _parse_fields_value(raw.get("FIELDS"))
    if fields is not None:
        return fields
    data = raw.get("data")
    if isinstance(data, dict):
        inner = _parse_fields_value(data.get("FIELDS"))
        if inner is not None:
            return inner
    return raw


def extract_leads_from_mock_json_root(payload: object) -> list[dict[str, Any]]:
    """Parse the root value of ``mock.json`` into a list of lead dicts.

    Supported shapes:

        * JSON array of objects (current repo ``mock.json``).
        * ``{"items"|"leads"|"records": [ ... ]}``.
        * ``{"data": [ ... ]}``.
        * ``{"data": {"FIELDS": {...}}}`` (single lead).

    Args:
        payload: Parsed JSON root (``list`` or ``dict``).

    Returns:
        Lead objects with uppercase Bitrix-style keys.

    Raises:
        ValueError: If the root shape is not recognized.
    """
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        raise ValueError("mock.json root must be a JSON array or object.")

    for key in ("items", "leads", "records"):
        bucket = payload.get(key)
        if isinstance(bucket, list):
            return [item for item in bucket if isinstance(item, dict)]

    data = payload.get("data")
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        fields = _parse_fields_value(data.get("FIELDS"))
        if fields is not None:
            return [fields]

    raise ValueError(
        "mock.json must be a list of objects, or an object with 'items', 'leads', "
        "'records', or 'data' (array or {FIELDS: {...}})."
    )
