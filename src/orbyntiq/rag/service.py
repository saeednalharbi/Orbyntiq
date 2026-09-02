from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
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
    timings_ms: dict[str, float] = field(default_factory=dict)


def _build_context(
    chunks: list[RetrievedChunk],
    chunk_character_limit: int,
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
                    chunk.text.strip()[:chunk_character_limit],
                ]
            )
        )

    return "\n\n".join(sections)


class RAGService:
    def __init__(
        self,
        *,
        retriever: SemanticRetriever,
        llm_service: LLMService,
        retrieval_limit: int = 3,
        chunk_character_limit: int = 700,
        max_output_tokens: int = 160,
    ) -> None:
        self._retriever = retriever
        self._llm_service = llm_service

        self._retrieval_limit = retrieval_limit
        self._chunk_character_limit = chunk_character_limit
        self._max_output_tokens = max_output_tokens

    async def answer(
        self,
        question: str,
        *,
        limit: int | None = None,
        score_threshold: float | None = 0.25,
        filters: RetrievalFilter | None = None,
    ) -> RAGAnswer:
        total_started = perf_counter()

        normalized_question = question.strip()

        if not normalized_question:
            raise ValueError("question cannot be empty")

        attributes: dict[str, object] = {
            "orbyntiq.rag.limit": limit,
            "orbyntiq.rag.filters_present": (filters is not None),
        }

        if score_threshold is not None:
            attributes["orbyntiq.rag.score_threshold"] = score_threshold

        with traced_span(
            "rag.answer",
            tracer_name="orbyntiq.rag",
            attributes=attributes,
        ) as span:
            retrieval_timings: dict[
                str,
                float,
            ] = {}

            chunks = await self._retriever.retrieve(
                normalized_question,
                limit=(self._retrieval_limit if limit is None else limit),
                score_threshold=score_threshold,
                filters=filters,
                timings_ms=retrieval_timings,
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
                    timings_ms={
                        **retrieval_timings,
                        "generation_ms": 0.0,
                        "total_ms": (perf_counter() - total_started) * 1000,
                    },
                )

            context = _build_context(
                chunks,
                chunk_character_limit=(self._chunk_character_limit),
            )

            prompt = (
                "Answer the question using only the retrieved "
                "context below. "
                "Be concise and focus only on information "
                "needed to answer the question. "
                "\n\n"
                f"Question:\n{normalized_question}\n\n"
                f"Retrieved context:\n{context}"
            )

            generation_started = perf_counter()

            response = await self._llm_service.chat(
                prompt,
                system_prompt=RAG_SYSTEM_PROMPT,
                max_tokens=self._max_output_tokens,
            )

            generation_ms = (perf_counter() - generation_started) * 1000

            answer = response.content.strip()

            if not answer:
                raise RAGGenerationError("LLM returned an empty RAG answer")

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
                timings_ms={
                    **retrieval_timings,
                    "generation_ms": generation_ms,
                    "total_ms": (perf_counter() - total_started) * 1000,
                },
            )
