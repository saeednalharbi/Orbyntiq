from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from orbyntiq.api.routes.knowledge import router
from orbyntiq.mcp.runtime import configure_mcp_services
from orbyntiq.rag.retrieval import RetrievedChunk


class FakeRetriever:
    async def retrieve(
        self,
        query: str,
        *,
        limit: int = 5,
        score_threshold: float | None = None,
        filters=None,
    ) -> list[RetrievedChunk]:
        del (
            limit,
            score_threshold,
            filters,
        )

        return [
            RetrievedChunk(
                id="chunk-1",
                score=0.91,
                document_id="document-1",
                chunk_index=0,
                text=("Qdrant stores Orbyntiq document embeddings."),
                source_path=("data/knowledge/orbyntiq.txt"),
                file_name="orbyntiq.txt",
                checksum="checksum-1",
                page_number=None,
            )
        ]


def make_qdrant():
    qdrant = SimpleNamespace()

    qdrant.get_collection = AsyncMock(
        return_value=SimpleNamespace(
            status=SimpleNamespace(value="green"),
            points_count=2,
            indexed_vectors_count=0,
            config=SimpleNamespace(
                params=SimpleNamespace(
                    vectors=SimpleNamespace(
                        size=1024,
                        distance=SimpleNamespace(value="Cosine"),
                    )
                )
            ),
        )
    )

    qdrant.scroll = AsyncMock(
        return_value=(
            [
                SimpleNamespace(
                    payload={
                        "document_id": "document-1",
                        "file_name": "orbyntiq.txt",
                        "source_path": ("data/knowledge/orbyntiq.txt"),
                        "checksum": "checksum-1",
                        "chunk_index": 0,
                        "text": "first",
                        "page_number": None,
                    }
                ),
                SimpleNamespace(
                    payload={
                        "document_id": "document-1",
                        "file_name": "orbyntiq.txt",
                        "source_path": ("data/knowledge/orbyntiq.txt"),
                        "checksum": "checksum-1",
                        "chunk_index": 1,
                        "text": "second",
                        "page_number": None,
                    }
                ),
            ],
            None,
        )
    )

    return qdrant


def make_client() -> TestClient:
    test_app = FastAPI()

    test_app.include_router(router)

    test_app.state.qdrant = make_qdrant()

    test_app.state.qdrant_available = True

    return TestClient(test_app)


def test_knowledge_status() -> None:
    client = make_client()

    response = client.get("/api/v1/knowledge/status")

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "green"
    assert payload["collection"] == ("orbyntiq_documents")
    assert payload["points_count"] == 2
    assert payload["indexed_vectors_count"] == 0
    assert payload["document_count"] == 1
    assert payload["vector_size"] == 1024
    assert payload["embedding_dimension"] == 1024


def test_list_knowledge_documents() -> None:
    client = make_client()

    response = client.get("/api/v1/knowledge/documents")

    assert response.status_code == 200

    payload = response.json()

    assert payload["count"] == 1

    document = payload["documents"][0]

    assert document["document_id"] == "document-1"

    assert document["file_name"] == "orbyntiq.txt"

    assert document["chunk_count"] == 2


def test_search_knowledge() -> None:
    configure_mcp_services(
        retriever=FakeRetriever(),
    )

    try:
        client = make_client()

        response = client.post(
            "/api/v1/knowledge/search",
            json={
                "query": "Where are embeddings stored?",
                "limit": 5,
            },
        )

        assert response.status_code == 200

        payload = response.json()

        assert payload["count"] == 1
        assert payload["results"][0]["score"] == 0.91
        assert payload["results"][0]["file_name"] == ("orbyntiq.txt")

    finally:
        configure_mcp_services()


def test_search_rejects_empty_query() -> None:
    configure_mcp_services(
        retriever=FakeRetriever(),
    )

    try:
        client = make_client()

        response = client.post(
            "/api/v1/knowledge/search",
            json={
                "query": "   ",
            },
        )

        assert response.status_code == 422

    finally:
        configure_mcp_services()


def test_ingest_rejects_unsupported_type() -> None:
    client = make_client()

    response = client.post(
        ("/api/v1/knowledge/ingest?file_name=malware.exe"),
        content=b"test",
        headers={
            "Content-Type": "application/octet-stream",
        },
    )

    assert response.status_code == 415
