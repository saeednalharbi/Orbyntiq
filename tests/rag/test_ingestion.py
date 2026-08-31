import asyncio
from unittest.mock import AsyncMock, Mock, patch

from orbyntiq.core.config import Settings
from orbyntiq.rag.chunking import TextChunker
from orbyntiq.rag.ingestion import DocumentIngestor


class FakeEmbeddings:
    dimension = 3

    async def embed_query(
        self,
        text: str,
    ) -> list[float]:
        return [1.0, 0.0, 0.0]

    async def embed_documents(
        self,
        texts,
    ) -> list[list[float]]:
        return [
            [1.0, 0.0, float(index)]
            for index, _ in enumerate(texts)
        ]

    async def close(self) -> None:
        return None


def test_ingestion_replaces_source_and_upserts_chunks(
    tmp_path,
) -> None:
    async def scenario() -> None:
        path = tmp_path / "knowledge.txt"
        path.write_text(
            (
                "Orbyntiq enterprise RAG knowledge. "
                "This text is long enough to create "
                "multiple deterministic chunks."
            ),
            encoding="utf-8",
        )

        qdrant = Mock()
        qdrant.delete = AsyncMock()
        qdrant.upsert = AsyncMock()

        settings = Settings(
            _env_file=None,
            embedding_dimension=3,
        )

        ingestor = DocumentIngestor(
            qdrant=qdrant,
            embeddings=FakeEmbeddings(),
            settings=settings,
            chunker=TextChunker(
                chunk_size=45,
                overlap=10,
            ),
        )

        with patch(
            "orbyntiq.rag.ingestion.ensure_qdrant_collection",
            new=AsyncMock(),
        ) as ensure_collection:
            result = await ingestor.ingest(path)

        ensure_collection.assert_awaited_once()

        qdrant.delete.assert_awaited_once()
        qdrant.upsert.assert_awaited_once()

        points = qdrant.upsert.await_args.kwargs[
            "points"
        ]

        assert result.chunks_indexed == len(points)
        assert result.chunks_indexed > 1

        assert all(
            point.payload["source_path"]
            == str(path.resolve())
            for point in points
        )

        assert all(
            "text" in point.payload
            for point in points
        )

    asyncio.run(scenario())