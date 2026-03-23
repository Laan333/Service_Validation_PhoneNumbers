from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize app resources."""
    configure_logging()
    yield


app = FastAPI(title="Phone Validator Service", version="0.1.0", lifespan=lifespan)
app.include_router(api_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "ok"}
