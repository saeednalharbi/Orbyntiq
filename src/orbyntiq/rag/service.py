from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from orbyntiq.observability.spans import (
    bounded_name,
    traced_span,
)
from orbyntiq.rag.prompts import (
    NO_CONTEXT_ANSWER,
    RAG_SYSTEM_PROMPT,
)
from orbyntiq.rag.retrieval import (
    RetrievalFilter,
    RetrievedChunk,
    SemanticRetriever,
)

if TYPE_CHECKING:
    from orbyntiq.services.llm_service import LLMService



class RAGGenerationError(RuntimeError):
    """Raised when grounded answer generation fails."""


@dataclass(frozen=True, slots=True)
class RAGSource:
    citation: str
    document_id: str
    file_name: str
    source_path: str
    chunk_index: int
    score: float
    page_number: int | None = None


@dataclass(frozen=True, slots=True)
class RAGAnswer:
    answer: str
    sources: tuple[RAGSource, ...]
    model: str | None


def _build_context(
    chunks: list[RetrievedChunk],
) -> str:
    sections: list[str] = []

    for index, chunk in enumerate(
        chunks,
        start=1,
    ):
        citation = f"S{index}"

        location = chunk.file_name

        if chunk.page_number is not None:
            location += f", page {chunk.page_number}"

        sections.append(
            "\n".join(
                [
                    f"[{citation}] {location}",
                    chunk.text,
                ]
            )
        )

    return "\n\n".join(
        sections
    )


class RAGService:
    def __init__(
        self,
        *,
        retriever: SemanticRetriever,
        llm_service: LLMService,
    ) -> None:
        self._retriever = retriever
        self._llm_service = llm_service

    async def answer(
        self,
        question: str,
        *,
        limit: int = 5,
        score_threshold: float | None = 0.25,
        filters: RetrievalFilter | None = None,
    ) -> RAGAnswer:
        normalized_question = question.strip()

        if not normalized_question:
            raise ValueError(
                "question cannot be empty"
            )

        attributes: dict[str, object] = {
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
            "rag.answer",
            tracer_name="orbyntiq.rag",
            attributes=attributes,
        ) as span:
            chunks = await self._retriever.retrieve(
                normalized_question,
                limit=limit,
                score_threshold=score_threshold,
                filters=filters,
            )

            span.set_attribute(
                "orbyntiq.rag.result_count",
                len(chunks),
            )

            if not chunks:
                span.set_attribute(
                    "orbyntiq.rag.status",
                    "no_context",
                )

                return RAGAnswer(
                    answer=NO_CONTEXT_ANSWER,
                    sources=(),
                    model=None,
                )

            context = _build_context(
                chunks
            )

            prompt = (
                "Answer the question using only the retrieved "
                "context below.\n\n"
                f"Question:\n{normalized_question}\n\n"
                f"Retrieved context:\n{context}"
            )

            response = await self._llm_service.chat(
                prompt,
                system_prompt=RAG_SYSTEM_PROMPT,
            )

            answer = response.content.strip()

            if not answer:
                raise RAGGenerationError(
                    "LLM returned an empty RAG answer"
                )

            sources = tuple(
                RAGSource(
                    citation=f"S{index}",
                    document_id=chunk.document_id,
                    file_name=chunk.file_name,
                    source_path=chunk.source_path,
                    chunk_index=chunk.chunk_index,
                    score=chunk.score,
                    page_number=chunk.page_number,
                )
                for index, chunk in enumerate(
                    chunks,
                    start=1,
                )
            )

            span.set_attribute(
                "orbyntiq.rag.source_count",
                len(sources),
            )

            span.set_attribute(
                "orbyntiq.rag.status",
                "success",
            )

            span.set_attribute(
                "gen_ai.response.model",
                bounded_name(
                    response.model,
                    default="unknown",
                ),
            )

            return RAGAnswer(
                answer=answer,
                sources=sources,
                model=response.model,
            )
