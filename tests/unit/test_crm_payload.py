"""Tests for CRM mock / Bitrix payload normalization (fixtures hardcoded; no env / file path)."""

import json
from typing import Any

import pytest

from app.schemas.webhook import CrmLeadPayload
from app.utils.crm_payload import extract_leads_from_mock_json_root, unwrap_bitrix_lead_body

# Mirrors ``mock.json`` object shape; kept inline so tests do not depend on MOCK_JSON_PATH or disk layout.
SAMPLE_MOCK_LEADS_FLAT: list[dict[str, Any]] = [
    {
        "ID": "190301",
        "TITLE": "New deal from James Carter",
        "STAGE_ID": "NEW",
        "CURRENCY_ID": "USD",
        "CONTACT_ID": "821001",
        "CONTACT_NAME": "James Carter",
        "CONTACT_EMAIL": "james@example.com",
        "CONTACT_PHONE": "(714) 883-9188",
        "SOURCE_ID": "WEB",
        "COMMENTS": "utm source: [b]google[/b]\nPage: [b]https://example.com/blog[/b]",
        "UTM_SOURCE": "google",
        "UTM_MEDIUM": "cpc",
        "UTM_CAMPAIGN": "{01_Performance_Elementary_tCPA}",
        "UTM_CONTENT": "{Elementary}",
        "DATE_CREATE": "2026-01-05T10:12:00+03:00",
    },
    {
        "ID": "190320",
        "TITLE": "New deal from Tom Walker",
        "STAGE_ID": "NEW",
        "CURRENCY_ID": "USD",
        "CONTACT_ID": "821020",
        "CONTACT_NAME": "Tom Walker",
        "CONTACT_EMAIL": "tom@example.com",
        "CONTACT_PHONE": "",
        "SOURCE_ID": "WEB",
        "COMMENTS": "Name: [b]Tom[/b]\nPhone: [b][/b]",
        "UTM_SOURCE": "google",
        "UTM_MEDIUM": "organic",
        "UTM_CAMPAIGN": "{01_Performance_Elementary_tCPA}",
        "UTM_CONTENT": "{Elementary}",
        "DATE_CREATE": "2026-03-05T08:00:00+03:00",
    },
]


def test_extract_and_validate_hardcoded_flat_array() -> None:
    leads = extract_leads_from_mock_json_root(SAMPLE_MOCK_LEADS_FLAT)
    assert len(leads) == 2
    for item in leads:
        CrmLeadPayload.model_validate(item)


def test_extract_from_items_wrapper() -> None:
    leads = extract_leads_from_mock_json_root({"items": [{"ID": "1", "CONTACT_PHONE": "x"}]})
    assert len(leads) == 1
    assert leads[0]["ID"] == "1"


def test_extract_from_data_fields_envelope() -> None:
    leads = extract_leads_from_mock_json_root(
        {"data": {"FIELDS": {"ID": "9", "CONTACT_PHONE": "+100", "TITLE": "T"}}}
    )
    assert len(leads) == 1
    CrmLeadPayload.model_validate(leads[0])


def test_unwrap_top_level_fields() -> None:
    flat = unwrap_bitrix_lead_body({"FIELDS": {"ID": "1", "CONTACT_PHONE": "4155552671"}})
    assert flat["ID"] == "1"


def test_unwrap_data_fields() -> None:
    flat = unwrap_bitrix_lead_body({"event": "x", "data": {"FIELDS": {"ID": "2", "CONTACT_PHONE": ""}}})
    assert flat["ID"] == "2"


def test_unwrap_fields_json_string() -> None:
    inner = json.dumps({"ID": "3", "CONTACT_PHONE": "123"})
    flat = unwrap_bitrix_lead_body({"FIELDS": inner})
    assert flat["ID"] == "3"


def test_extract_invalid_root_raises() -> None:
    with pytest.raises(ValueError):
        extract_leads_from_mock_json_root("not-a-list")
