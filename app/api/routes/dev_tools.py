import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/dev", tags=["dev"])


def _resolve_mock_path() -> Path:
    docker_path = Path("/app/mock.json")
    local_path = Path.cwd() / "mock.json"
    if docker_path.exists():
        return docker_path
    if local_path.exists():
        return local_path
    raise FileNotFoundError("mock.json not found.")


@router.get("/mock-leads")
async def get_mock_leads() -> dict[str, list[dict[str, Any]]]:
    """Return mock leads for replay testing from the official mock payload file."""
    try:
        path = _resolve_mock_path()
        with path.open("r", encoding="utf-8") as file_obj:
            payload = json.load(file_obj)
        if not isinstance(payload, list):
            raise ValueError("mock.json root value must be a list.")
        typed_payload = [item for item in payload if isinstance(item, dict)]
        logger.info("Loaded %s mock leads from %s", len(typed_payload), path)
        return {"items": typed_payload}
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        logger.exception("Failed to load mock leads: %s", exc)
        raise HTTPException(status_code=500, detail="Unable to load mock leads for replay.") from exc
