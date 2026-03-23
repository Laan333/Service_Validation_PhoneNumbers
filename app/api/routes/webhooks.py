from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import ValidationError

from app.api.deps import get_pipeline, verify_webhook_token
from app.schemas.webhook import CrmLeadPayload, WebhookValidationResponse
from app.services.phone_pipeline import PhoneValidationPipeline
from app.utils.crm_payload import unwrap_bitrix_lead_body

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/crm/lead", response_model=WebhookValidationResponse)
async def handle_crm_lead(
    body: Annotated[dict[str, Any], Body(...)],
    _: Annotated[None, Depends(verify_webhook_token)],
    pipeline: Annotated[PhoneValidationPipeline, Depends(get_pipeline)],
) -> WebhookValidationResponse:
    """Process incoming CRM lead payload (flat Bitrix fields or FIELDS/data envelope)."""
    flat = unwrap_bitrix_lead_body(body)
    try:
        payload = CrmLeadPayload.model_validate(flat)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc
    result = await pipeline.process(payload.id, payload.contact_phone or "")
    return WebhookValidationResponse(
        lead_id=payload.id,
        status=result.status,
        normalized_phone=result.normalized_phone,
        reason=result.reason.value if result.reason else None,
        source=result.source,
    )
