import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/dev", tags=["dev"])


class MockLeadsResponse(BaseModel):
    """Mock CRM payloads for replay plus resolved file path (for debugging)."""

    items: list[dict[str, Any]]
    source_path: str = Field(description="Absolute path of the JSON file that was read.")


def _repo_root() -> Path:
    """Parent of the `app` package (WORKDIR `/app` in Docker, git root locally)."""
    return Path(__file__).resolve().parents[3]


def _resolve_mock_path() -> Path:
    """Resolve mock.json: optional MOCK_JSON_PATH, then repo root, then `/app/mock.json`."""
    raw = (settings.mock_json_path or "").strip()
    if raw:
        configured = Path(raw)
        if not configured.is_absolute():
            configured = _repo_root() / configured
        if configured.is_file():
            return configured
        logger.warning("MOCK_JSON_PATH is set but not a file (%s); using defaults.", configured)

    for candidate in (_repo_root() / "mock.json", Path("/app/mock.json")):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("mock.json not found.")


@router.get("/mock-leads", response_model=MockLeadsResponse)
async def get_mock_leads() -> MockLeadsResponse:
    """Return mock leads for replay testing from the official mock payload file."""
    try:
        path = _resolve_mock_path()
        resolved = str(path.resolve())
        with path.open("r", encoding="utf-8") as file_obj:
            payload = json.load(file_obj)
        if not isinstance(payload, list):
            raise ValueError("mock.json root value must be a list.")
        typed_payload = [item for item in payload if isinstance(item, dict)]
        logger.info("Loaded %s mock leads from %s", len(typed_payload), resolved)
        return MockLeadsResponse(items=typed_payload, source_path=resolved)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        logger.exception("Failed to load mock leads: %s", exc)
        raise HTTPException(status_code=500, detail="Unable to load mock leads for replay.") from exc
