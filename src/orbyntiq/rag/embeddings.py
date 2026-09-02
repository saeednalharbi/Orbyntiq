from collections.abc import Sequence
from typing import Protocol

import httpx

from orbyntiq.core.config import Settings


class EmbeddingError(RuntimeError):
    """Raised when embedding generation fails."""


class EmbeddingProvider(Protocol):
    dimension: int

    async def embed_query(self, text: str) -> list[float]: ...

    async def embed_documents(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]: ...

    async def close(self) -> None: ...


class OllamaEmbeddingProvider:
    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.model = settings.embedding_model
        self.dimension = settings.embedding_dimension
        self._owns_client = client is None

        self._client = client or httpx.AsyncClient(
            base_url=settings.ollama_base_url.rstrip("/"),
            timeout=settings.embedding_timeout_seconds,
        )

    async def _embed(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        normalized = [text.strip() for text in texts]

        if not normalized:
            raise ValueError("texts cannot be empty")

        if any(not text for text in normalized):
            raise ValueError("embedding text cannot be empty")

        try:
            response = await self._client.post(
                "/api/embed",
                json={
                    "model": self.model,
                    "input": normalized,
                    "keep_alive": "0",
                },
            )
            response.raise_for_status()
            payload = response.json()
            embeddings = payload["embeddings"]
        except (
            httpx.HTTPError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise EmbeddingError("Failed to generate embeddings") from exc

        if not isinstance(embeddings, list) or len(embeddings) != len(normalized):
            raise EmbeddingError("Embedding response has an invalid shape")

        vectors: list[list[float]] = []

        for embedding in embeddings:
            if not isinstance(embedding, list):
                raise EmbeddingError("Embedding response contains an invalid vector")

            try:
                vector = [float(value) for value in embedding]
            except (TypeError, ValueError) as exc:
                raise EmbeddingError("Embedding vector contains invalid values") from exc

            if len(vector) != self.dimension:
                raise EmbeddingError(
                    f"Embedding dimension mismatch: expected {self.dimension}, got {len(vector)}"
                )

            vectors.append(vector)

        return vectors

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self._embed([text])
        return vectors[0]

    async def embed_documents(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        return await self._embed(texts)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()


def create_embedding_provider(
    settings: Settings,
) -> EmbeddingProvider:
    if settings.embedding_provider == "ollama":
        return OllamaEmbeddingProvider(settings)

    raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")
