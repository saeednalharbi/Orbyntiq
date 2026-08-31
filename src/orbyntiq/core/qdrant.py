from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import (
    ResponseHandlingException,
    UnexpectedResponse,
)

from orbyntiq.core.config import Settings


class QdrantUnavailableError(RuntimeError):
    """Raised when Qdrant cannot be reached or fails its health check."""


def create_qdrant_client(settings: Settings) -> AsyncQdrantClient:
    return AsyncQdrantClient(
        url=settings.qdrant_url,
        grpc_port=settings.qdrant_grpc_port,
        prefer_grpc=settings.qdrant_prefer_grpc,
        timeout=settings.qdrant_timeout_seconds,
    )


async def verify_qdrant_connection(client: AsyncQdrantClient) -> None:
    try:
        await client.get_collections()
    except (ResponseHandlingException, UnexpectedResponse, OSError) as exc:
        raise QdrantUnavailableError("Qdrant is unavailable") from exc


async def close_qdrant_client(client: AsyncQdrantClient) -> None:
    await client.close()
