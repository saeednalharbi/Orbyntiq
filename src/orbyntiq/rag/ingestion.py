from dataclasses import dataclass
from pathlib import Path

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointStruct,
)

from orbyntiq.core.config import Settings
from orbyntiq.core.qdrant_schema import ensure_qdrant_collection
from orbyntiq.rag.chunking import TextChunker
from orbyntiq.rag.documents import load_document
from orbyntiq.rag.embeddings import EmbeddingProvider


class IngestionError(RuntimeError):
    """Raised when document ingestion fails."""


@dataclass(frozen=True, slots=True)
class IngestionResult:
    document_id: str
    checksum: str
    chunks_indexed: int


class DocumentIngestor:
    def __init__(
        self,
        *,
        qdrant: AsyncQdrantClient,
        embeddings: EmbeddingProvider,
        settings: Settings,
        chunker: TextChunker | None = None,
    ) -> None:
        self._qdrant = qdrant
        self._embeddings = embeddings
        self._settings = settings
        self._chunker = chunker or TextChunker()

    async def ingest(
        self,
        path: str | Path,
    ) -> IngestionResult:
        document = load_document(path)
        chunks = self._chunker.split(document)

        if not chunks:
            raise IngestionError(
                "Document produced no chunks"
            )

        vectors = await self._embeddings.embed_documents(
            [chunk.text for chunk in chunks]
        )

        if len(vectors) != len(chunks):
            raise IngestionError(
                "Embedding count does not match chunk count"
            )

        await ensure_qdrant_collection(
            self._qdrant,
            self._settings,
        )

        selector = FilterSelector(
            filter=Filter(
                must=[
                    FieldCondition(
                        key="source_path",
                        match=MatchValue(
                            value=document.source_path
                        ),
                    )
                ]
            )
        )

        await self._qdrant.delete(
            collection_name=self._settings.qdrant_collection,
            points_selector=selector,
            wait=True,
        )

        points = [
            PointStruct(
                id=chunk.id,
                vector=vector,
                payload={
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "source_path": chunk.source_path,
                    "file_name": chunk.file_name,
                    "checksum": chunk.checksum,
                    "page_number": chunk.page_number,
                },
            )
            for chunk, vector in zip(
                chunks,
                vectors,
                strict=True,
            )
        ]

        await self._qdrant.upsert(
            collection_name=self._settings.qdrant_collection,
            points=points,
            wait=True,
        )

        return IngestionResult(
            document_id=document.id,
            checksum=document.checksum,
            chunks_indexed=len(chunks),
        )