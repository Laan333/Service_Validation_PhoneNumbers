from fastapi import APIRouter

from app.api.routes.metrics import router as metrics_router
from app.api.routes.webhooks import router as webhooks_router

api_router = APIRouter()
api_router.include_router(webhooks_router)
api_router.include_router(metrics_router)
