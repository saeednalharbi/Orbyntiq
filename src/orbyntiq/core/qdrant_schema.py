from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import (
    ResponseHandlingException,
    UnexpectedResponse,
)
from qdrant_client.models import Distance, VectorParams

from orbyntiq.core.config import Settings


class QdrantSchemaError(RuntimeError):
    """Raised when the Qdrant collection schema is invalid."""


async def ensure_qdrant_collection(
    client: AsyncQdrantClient,
    settings: Settings,
) -> None:
    try:
        collections = await client.get_collections()

        collection_exists = any(
            collection.name == settings.qdrant_collection
            for collection in collections.collections
        )

        if not collection_exists:
            await client.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(
                    size=settings.embedding_dimension,
                    distance=Distance.COSINE,
                ),
            )
            return

        info = await client.get_collection(
            settings.qdrant_collection
        )

    except (
        ResponseHandlingException,
        UnexpectedResponse,
        OSError,
    ) as exc:
        raise QdrantSchemaError(
            "Failed to initialize Qdrant collection"
        ) from exc

    vectors = info.config.params.vectors
    vector_size = getattr(vectors, "size", None)

    if vector_size != settings.embedding_dimension:
        raise QdrantSchemaError(
            "Qdrant vector dimension mismatch: "
            f"expected {settings.embedding_dimension}, "
            f"got {vector_size}"
        )