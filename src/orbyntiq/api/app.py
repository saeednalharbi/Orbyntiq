from fastapi import FastAPI

from orbyntiq.core.config import get_settings
from orbyntiq.core.logging import configure_logging, get_logger

settings = get_settings()

configure_logging()

logger = get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.environment,
    }