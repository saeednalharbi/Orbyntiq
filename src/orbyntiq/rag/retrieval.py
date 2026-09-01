from dataclasses import dataclass

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import (
    ResponseHandlingException,
    UnexpectedResponse,
)
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
)

from orbyntiq.core.config import Settings
from orbyntiq.observability.spans import (
    bounded_name,
    traced_span,
)
from orbyntiq.rag.embeddings import EmbeddingProvider


class RetrievalError(RuntimeError):
    """Raised when semantic retrieval fails."""


@dataclass(frozen=True, slots=True)
class RetrievalFilter:
    document_id: str | None = None
    source_path: str | None = None
    file_name: str | None = None
    checksum: str | None = None

    def to_qdrant_filter(self) -> Filter | None:
        conditions: list[FieldCondition] = []

        values = {
            "document_id": self.document_id,
            "source_path": self.source_path,
            "file_name": self.file_name,
            "checksum": self.checksum,
        }

        for key, value in values.items():
            if value is None:
                continue

            normalized = value.strip()

            if not normalized:
                raise ValueError(
                    f"{key} filter cannot be empty"
                )

            conditions.append(
                FieldCondition(
                    key=key,
                    match=MatchValue(
                        value=normalized
                    ),
                )
            )

        if not conditions:
            return None

        return Filter(
            must=conditions
        )


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    id: str
    score: float
    document_id: str
    chunk_index: int
    text: str
    source_path: str
    file_name: str
    checksum: str
    page_number: int | None = None


class SemanticRetriever:
    def __init__(
        self,
        *,
        qdrant: AsyncQdrantClient,
        embeddings: EmbeddingProvider,
        settings: Settings,
    ) -> None:
        self._qdrant = qdrant
        self._embeddings = embeddings
        self._settings = settings

    async def retrieve(
        self,
        query: str,
        *,
        limit: int = 5,
        score_threshold: float | None = None,
        filters: RetrievalFilter | None = None,
    ) -> list[RetrievedChunk]:
        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError(
                "query cannot be empty"
            )

        if limit < 1 or limit > 50:
            raise ValueError(
                "limit must be between 1 and 50"
            )

        if (
            score_threshold is not None
            and not -1.0 <= score_threshold <= 1.0
        ):
            raise ValueError(
                "score_threshold must be between -1 and 1"
            )

        attributes: dict[str, object] = {
            "gen_ai.operation.name": "retrieval",
            "orbyntiq.rag.limit": limit,
            "orbyntiq.rag.filters_present": (
                filters is not None
            ),
        }

        if score_threshold is not None:
            attributes[
                "orbyntiq.rag.score_threshold"
            ] = score_threshold

        with traced_span(
            "rag.retrieve",
            tracer_name="orbyntiq.rag",
            attributes=attributes,
        ) as span:
            with traced_span(
                "embedding.query",
                tracer_name="orbyntiq.rag",
                attributes={
                    "gen_ai.operation.name": "embeddings",
                    "orbyntiq.embedding.provider": bounded_name(
                        type(
                            self._embeddings
                        ).__name__,
                        default="unknown",
                    ),
                },
            ):
                query_vector = (
                    await self._embeddings.embed_query(
                        normalized_query
                    )
                )

            query_filter = (
                filters.to_qdrant_filter()
                if filters is not None
                else None
            )

            collection = bounded_name(
                self._settings.qdrant_collection,
                default="unknown",
            )

            with traced_span(
                "qdrant.search",
                tracer_name="orbyntiq.rag",
                attributes={
                    "db.system.name": "qdrant",
                    "db.collection.name": collection,
                    "orbyntiq.qdrant.limit": limit,
                },
            ) as qdrant_span:
                try:
                    response = (
                        await self._qdrant.query_points(
                            collection_name=(
                                self._settings.qdrant_collection
                            ),
                            query=query_vector,
                            query_filter=query_filter,
                            with_payload=True,
                            with_vectors=False,
                            limit=limit,
                            score_threshold=score_threshold,
                        )
                    )

                except (
                    ResponseHandlingException,
                    UnexpectedResponse,
                    OSError,
                ) as exc:
                    raise RetrievalError(
                        "Semantic retrieval failed"
                    ) from exc

                qdrant_span.set_attribute(
                    "orbyntiq.qdrant.result_count",
                    len(response.points),
                )

            results: list[RetrievedChunk] = []

            for point in response.points:
                payload = point.payload or {}

                try:
                    document_id = str(
                        payload["document_id"]
                    )
                    chunk_index = int(
                        payload["chunk_index"]
                    )
                    text = str(
                        payload["text"]
                    )
                    source_path = str(
                        payload["source_path"]
                    )
                    file_name = str(
                        payload["file_name"]
                    )
                    checksum = str(
                        payload["checksum"]
                    )

                    raw_page_number = payload.get(
                        "page_number"
                    )

                    page_number = (
                        None
                        if raw_page_number is None
                        else int(
                            raw_page_number
                        )
                    )

                except (
                    KeyError,
                    TypeError,
                    ValueError,
                ) as exc:
                    raise RetrievalError(
                        "Retrieved point contains invalid payload"
                    ) from exc

                if not text.strip():
                    raise RetrievalError(
                        "Retrieved point contains empty text"
                    )

                results.append(
                    RetrievedChunk(
                        id=str(point.id),
                        score=float(point.score),
                        document_id=document_id,
                        chunk_index=chunk_index,
                        text=text,
                        source_path=source_path,
                        file_name=file_name,
                        checksum=checksum,
                        page_number=page_number,
                    )
                )

            span.set_attribute(
                "orbyntiq.rag.result_count",
                len(results),
            )

            return results
