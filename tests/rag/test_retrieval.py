import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from orbyntiq.core.config import Settings
from orbyntiq.rag.retrieval import (
    RetrievalFilter,
    SemanticRetriever,
)


class FakeEmbeddings:
    dimension = 3

    async def embed_query(
        self,
        text: str,
    ) -> list[float]:
        assert text == "enterprise rag"
        return [1.0, 0.0, 0.0]

    async def embed_documents(
        self,
        texts,
    ) -> list[list[float]]:
        return []

    async def close(self) -> None:
        return None


def test_retrieval_returns_ranked_chunks() -> None:
    async def scenario() -> None:
        qdrant = Mock()

        qdrant.query_points = AsyncMock(
            return_value=SimpleNamespace(
                points=[
                    SimpleNamespace(
                        id="point-1",
                        score=0.91,
                        payload={
                            "document_id": "document-1",
                            "chunk_index": 0,
                            "text": "Enterprise RAG knowledge",
                            "source_path": "knowledge.txt",
                            "file_name": "knowledge.txt",
                            "checksum": "abc",
                            "page_number": None,
                        },
                    )
                ]
            )
        )

        retriever = SemanticRetriever(
            qdrant=qdrant,
            embeddings=FakeEmbeddings(),
            settings=Settings(
                _env_file=None,
                embedding_dimension=3,
            ),
        )

        results = await retriever.retrieve(
            "enterprise rag"
        )

        assert len(results) == 1
        assert results[0].score == 0.91
        assert results[0].text == (
            "Enterprise RAG knowledge"
        )

        qdrant.query_points.assert_awaited_once()

    asyncio.run(scenario())


def test_retrieval_passes_metadata_filter() -> None:
    async def scenario() -> None:
        qdrant = Mock()

        qdrant.query_points = AsyncMock(
            return_value=SimpleNamespace(points=[])
        )

        retriever = SemanticRetriever(
            qdrant=qdrant,
            embeddings=FakeEmbeddings(),
            settings=Settings(
                _env_file=None,
                embedding_dimension=3,
            ),
        )

        await retriever.retrieve(
            "enterprise rag",
            filters=RetrievalFilter(
                document_id="document-1"
            ),
        )

        kwargs = qdrant.query_points.await_args.kwargs
        query_filter = kwargs["query_filter"]

        assert query_filter is not None
        assert len(query_filter.must) == 1

        condition = query_filter.must[0]

        assert condition.key == "document_id"
        assert condition.match.value == "document-1"

    asyncio.run(scenario())


def test_retrieval_passes_score_threshold() -> None:
    async def scenario() -> None:
        qdrant = Mock()

        qdrant.query_points = AsyncMock(
            return_value=SimpleNamespace(points=[])
        )

        retriever = SemanticRetriever(
            qdrant=qdrant,
            embeddings=FakeEmbeddings(),
            settings=Settings(
                _env_file=None,
                embedding_dimension=3,
            ),
        )

        await retriever.retrieve(
            "enterprise rag",
            limit=3,
            score_threshold=0.5,
        )

        kwargs = qdrant.query_points.await_args.kwargs

        assert kwargs["limit"] == 3
        assert kwargs["score_threshold"] == 0.5

    asyncio.run(scenario())


def test_retrieval_rejects_empty_query() -> None:
    retriever = SemanticRetriever(
        qdrant=Mock(),
        embeddings=FakeEmbeddings(),
        settings=Settings(
            _env_file=None,
            embedding_dimension=3,
        ),
    )

    with pytest.raises(
        ValueError,
        match="query cannot be empty",
    ):
        asyncio.run(
            retriever.retrieve("   ")
        )


@pytest.mark.parametrize(
    "limit",
    [0, 51],
)
def test_retrieval_rejects_invalid_limit(
    limit,
) -> None:
    retriever = SemanticRetriever(
        qdrant=Mock(),
        embeddings=FakeEmbeddings(),
        settings=Settings(
            _env_file=None,
            embedding_dimension=3,
        ),
    )

    with pytest.raises(
        ValueError,
        match="limit must be between",
    ):
        asyncio.run(
            retriever.retrieve(
                "enterprise rag",
                limit=limit,
            )
        )


def test_filter_rejects_empty_value() -> None:
    filters = RetrievalFilter(
        source_path="   "
    )

    with pytest.raises(
        ValueError,
        match="source_path filter cannot be empty",
    ):
        filters.to_qdrant_filter()