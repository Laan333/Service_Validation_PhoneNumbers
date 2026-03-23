"""Pytest fixtures shared across the suite."""

import pytest

from app.core import config


@pytest.fixture(autouse=True)
def disable_external_ip_geo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid flaky HTTP calls to ipapi.co during tests; use default country only."""
    monkeypatch.setattr(config.settings, "ip_geo_enabled", False)
