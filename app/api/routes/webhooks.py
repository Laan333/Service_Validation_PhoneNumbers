from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_pipeline, verify_webhook_token
from app.schemas.webhook import CrmLeadPayload, WebhookValidationResponse
from app.services.phone_pipeline import PhoneValidationPipeline

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/crm/lead", response_model=WebhookValidationResponse)
async def handle_crm_lead(
    payload: CrmLeadPayload,
    _: Annotated[None, Depends(verify_webhook_token)],
    pipeline: Annotated[PhoneValidationPipeline, Depends(get_pipeline)],
) -> WebhookValidationResponse:
    """Process incoming CRM lead payload."""
    result = await pipeline.process(payload.id, payload.contact_phone)
    return WebhookValidationResponse(
        lead_id=payload.id,
        status=result.status,
        normalized_phone=result.normalized_phone,
        reason=result.reason.value if result.reason else None,
        source=result.source,
    )
