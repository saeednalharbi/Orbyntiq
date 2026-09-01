from dataclasses import asdict
from typing import Any

from orbyntiq.agents.contracts import AgentResult, AgentStatus
from orbyntiq.agents.state import AgentState
from orbyntiq.rag import (
    RAGGenerationError,
    RAGService,
    RetrievalError,
)


class ResearchAgent:
    """Answer knowledge-base questions through Orbyntiq RAG."""

    def __init__(self, rag_service: RAGService) -> None:
        self._rag_service = rag_service

    async def __call__(self, state: AgentState) -> dict[str, Any]:
        """Execute grounded retrieval and return a partial graph update."""

        try:
            answer = await self._rag_service.answer(
                state["user_query"],
            )
        except (RetrievalError, RAGGenerationError) as exc:
            error_message = str(exc)

            result = AgentResult(
                agent="research",
                status=AgentStatus.FAILED,
                error=error_message,
                metadata={
                    "error_type": type(exc).__name__,
                },
            )

            return {
                "active_agent": "research",
                "agent_results": [
                    result.model_dump(mode="json"),
                ],
                "errors": [error_message],
                "hop_count": state["hop_count"] + 1,
            }

        sources = [
            asdict(source)
            for source in answer.sources
        ]

        result = AgentResult(
            agent="research",
            status=AgentStatus.SUCCESS,
            content=answer.answer,
            metadata={
                "model": answer.model,
                "source_count": len(sources),
            },
            sources=sources,
        )

        return {
            "active_agent": "research",
            "agent_results": [
                result.model_dump(mode="json"),
            ],
            "sources": sources,
            "hop_count": state["hop_count"] + 1,
        }
