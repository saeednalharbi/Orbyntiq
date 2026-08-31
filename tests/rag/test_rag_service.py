import asyncio

import pytest

from orbyntiq.llm.models import LLMResponse
from orbyntiq.rag.prompts import NO_CONTEXT_ANSWER
from orbyntiq.rag.retrieval import RetrievedChunk
from orbyntiq.rag.service import (
    RAGGenerationError,
    RAGService,
)


class FakeRetriever:
    def __init__(
        self,
        chunks: list[RetrievedChunk],
    ) -> None:
        self.chunks = chunks
        self.last_query: str | None = None

    async def retrieve(
        self,
        query: str,
        *,
        limit: int = 5,
        score_threshold: float | None = None,
        filters=None,
    ) -> list[RetrievedChunk]:
        self.last_query = query
        return self.chunks


class FakeLLMService:
    def __init__(
        self,
        response: str = "Qdrant stores the embeddings [S1].",
    ) -> None:
        self.response = response
        self.called = False
        self.last_prompt: str | None = None
        self.last_system_prompt: str | None = None

    async def chat(
        self,
        prompt: str,
        *,
        system_prompt: str,
        history=(),
    ) -> LLMResponse:
        self.called = True
        self.last_prompt = prompt
        self.last_system_prompt = system_prompt

        return LLMResponse(
            content=self.response,
            model="fake-model",
        )


def make_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        id="chunk-1",
        score=0.91,
        document_id="document-1",
        chunk_index=0,
        text="Qdrant stores document embeddings.",
        source_path="/knowledge/platform.txt",
        file_name="platform.txt",
        checksum="abc123",
        page_number=None,
    )


def test_rag_answer_uses_retrieved_context() -> None:
    async def scenario() -> None:
        retriever = FakeRetriever([make_chunk()])
        llm = FakeLLMService()

        service = RAGService(
            retriever=retriever,  # type: ignore[arg-type]
            llm_service=llm,  # type: ignore[arg-type]
        )

        result = await service.answer(
            "What stores document embeddings?"
        )

        assert result.answer == (
            "Qdrant stores the embeddings [S1]."
        )
        assert result.model == "fake-model"
        assert len(result.sources) == 1
        assert result.sources[0].citation == "S1"
        assert result.sources[0].file_name == "platform.txt"

        assert llm.called is True
        assert "[S1] platform.txt" in llm.last_prompt
        assert (
            "Qdrant stores document embeddings."
            in llm.last_prompt
        )

    asyncio.run(scenario())


def test_rag_returns_safe_answer_without_context() -> None:
    async def scenario() -> None:
        retriever = FakeRetriever([])
        llm = FakeLLMService()

        service = RAGService(
            retriever=retriever,  # type: ignore[arg-type]
            llm_service=llm,  # type: ignore[arg-type]
        )

        result = await service.answer(
            "Unknown knowledge question"
        )

        assert result.answer == NO_CONTEXT_ANSWER
        assert result.sources == ()
        assert result.model is None
        assert llm.called is False

    asyncio.run(scenario())


def test_rag_preserves_page_source() -> None:
    async def scenario() -> None:
        chunk = RetrievedChunk(
            id="chunk-1",
            score=0.88,
            document_id="document-1",
            chunk_index=2,
            text="Architecture detail.",
            source_path="/docs/report.pdf",
            file_name="report.pdf",
            checksum="abc",
            page_number=7,
        )

        llm = FakeLLMService(
            "The detail is shown on page 7 [S1]."
        )

        service = RAGService(
            retriever=FakeRetriever(
                [chunk]
            ),  # type: ignore[arg-type]
            llm_service=llm,  # type: ignore[arg-type]
        )

        result = await service.answer("Where is it?")

        assert result.sources[0].page_number == 7
        assert "[S1] report.pdf, page 7" in llm.last_prompt

    asyncio.run(scenario())


def test_rag_rejects_empty_question() -> None:
    service = RAGService(
        retriever=FakeRetriever(
            []
        ),  # type: ignore[arg-type]
        llm_service=FakeLLMService(),  # type: ignore[arg-type]
    )

    with pytest.raises(
        ValueError,
        match="question cannot be empty",
    ):
        asyncio.run(service.answer("   "))


def test_rag_rejects_empty_llm_answer() -> None:
    async def scenario() -> None:
        service = RAGService(
            retriever=FakeRetriever(
                [make_chunk()]
            ),  # type: ignore[arg-type]
            llm_service=FakeLLMService(
                "   "
            ),  # type: ignore[arg-type]
        )

        with pytest.raises(
            RAGGenerationError,
            match="empty RAG answer",
        ):
            await service.answer(
                "What stores embeddings?"
            )

    asyncio.run(scenario())