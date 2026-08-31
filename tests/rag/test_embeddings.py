import asyncio
import json

import httpx
import pytest

from orbyntiq.core.config import Settings
from orbyntiq.rag.embeddings import (
    EmbeddingError,
    OllamaEmbeddingProvider,
)


def test_embed_query_returns_expected_vector() -> None:
    async def scenario() -> None:
        def handler(
            request: httpx.Request,
        ) -> httpx.Response:
            payload = json.loads(request.content)

            assert payload["model"] == "test-embedding"
            assert payload["input"] == ["hello"]

            return httpx.Response(
                200,
                json={
                    "embeddings": [
                        [0.1, 0.2, 0.3, 0.4]
                    ]
                },
            )

        settings = Settings(
            _env_file=None,
            embedding_model="test-embedding",
            embedding_dimension=4,
        )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="http://test",
        ) as client:
            provider = OllamaEmbeddingProvider(
                settings,
                client=client,
            )

            vector = await provider.embed_query("hello")

        assert vector == [0.1, 0.2, 0.3, 0.4]

    asyncio.run(scenario())


def test_embed_documents_batches_inputs() -> None:
    async def scenario() -> None:
        def handler(
            request: httpx.Request,
        ) -> httpx.Response:
            payload = json.loads(request.content)

            assert payload["input"] == ["first", "second"]

            return httpx.Response(
                200,
                json={
                    "embeddings": [
                        [0.1, 0.2],
                        [0.3, 0.4],
                    ]
                },
            )

        settings = Settings(
            _env_file=None,
            embedding_dimension=2,
        )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="http://test",
        ) as client:
            provider = OllamaEmbeddingProvider(
                settings,
                client=client,
            )

            vectors = await provider.embed_documents(
                ["first", "second"]
            )

        assert vectors == [
            [0.1, 0.2],
            [0.3, 0.4],
        ]

    asyncio.run(scenario())


def test_embedding_rejects_empty_text() -> None:
    settings = Settings(
        _env_file=None,
        embedding_dimension=2,
    )

    provider = OllamaEmbeddingProvider(settings)

    with pytest.raises(
        ValueError,
        match="embedding text cannot be empty",
    ):
        asyncio.run(provider.embed_query("   "))

    asyncio.run(provider.close())


def test_embedding_rejects_wrong_dimension() -> None:
    async def scenario() -> None:
        def handler(
            request: httpx.Request,
        ) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "embeddings": [
                        [0.1, 0.2]
                    ]
                },
            )

        settings = Settings(
            _env_file=None,
            embedding_dimension=3,
        )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="http://test",
        ) as client:
            provider = OllamaEmbeddingProvider(
                settings,
                client=client,
            )

            with pytest.raises(
                EmbeddingError,
                match="Embedding dimension mismatch",
            ):
                await provider.embed_query("hello")

    asyncio.run(scenario())