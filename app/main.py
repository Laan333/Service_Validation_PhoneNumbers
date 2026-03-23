from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize app resources."""
    configure_logging()
    base_url = f"http://{settings.public_host}:{settings.nginx_port}"
    logger.info("Phone Validator Service is up. Open UI at %s", base_url)
    logger.info("Health endpoint: %s/health", base_url)
    logger.info("Webhook endpoint: %s/api/v1/webhooks/crm/lead", base_url)
    yield


app = FastAPI(title="Phone Validator Service", version="0.1.0", lifespan=lifespan)
app.include_router(api_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "ok"}
