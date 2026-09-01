import asyncio
from unittest.mock import AsyncMock, MagicMock

from orbyntiq.agents.contracts import AgentStatus
from orbyntiq.agents.research import ResearchAgent
from orbyntiq.agents.state import create_initial_state
from orbyntiq.rag import (
    RAGAnswer,
    RAGService,
    RAGSource,
    RetrievalError,
)


def make_source() -> RAGSource:
    return RAGSource(
        citation="S1",
        document_id="document-1",
        file_name="employee-policy.pdf",
        source_path="/knowledge/employee-policy.pdf",
        chunk_index=2,
        score=0.93,
        page_number=7,
    )


def test_research_agent_returns_grounded_result() -> None:
    service = MagicMock(spec=RAGService)
    service.answer = AsyncMock(
        return_value=RAGAnswer(
            answer="Remote work is permitted [S1].",
            sources=(make_source(),),
            model="qwen3:4b-instruct",
        )
    )

    agent = ResearchAgent(service)
    state = create_initial_state(
        "What does the employee policy say about remote work?"
    )

    update = asyncio.run(agent(state))

    assert update["active_agent"] == "research"
    assert update["hop_count"] == 1

    assert len(update["agent_results"]) == 1

    result = update["agent_results"][0]

    assert result["agent"] == "research"
    assert result["status"] == AgentStatus.SUCCESS
    assert result["content"] == "Remote work is permitted [S1]."
    assert result["metadata"]["model"] == "qwen3:4b-instruct"
    assert result["metadata"]["source_count"] == 1
    assert result["error"] is None

    assert len(update["sources"]) == 1
    assert update["sources"][0]["citation"] == "S1"
    assert update["sources"][0]["document_id"] == "document-1"
    assert update["sources"][0]["file_name"] == "employee-policy.pdf"
    assert update["sources"][0]["page_number"] == 7

    service.answer.assert_awaited_once_with(
        "What does the employee policy say about remote work?"
    )


def test_research_agent_handles_no_context_answer() -> None:
    service = MagicMock(spec=RAGService)
    service.answer = AsyncMock(
        return_value=RAGAnswer(
            answer=(
                "I couldn't find sufficiently relevant information "
                "in the indexed knowledge base."
            ),
            sources=(),
            model=None,
        )
    )

    agent = ResearchAgent(service)
    state = create_initial_state(
        "What is the secret internal launch date?"
    )

    update = asyncio.run(agent(state))

    result = update["agent_results"][0]

    assert result["status"] == AgentStatus.SUCCESS
    assert result["metadata"]["source_count"] == 0
    assert result["metadata"]["model"] is None
    assert result["sources"] == []
    assert update["sources"] == []


def test_research_agent_handles_retrieval_failure() -> None:
    service = MagicMock(spec=RAGService)
    service.answer = AsyncMock(
        side_effect=RetrievalError(
            "Semantic retrieval failed"
        )
    )

    agent = ResearchAgent(service)
    state = create_initial_state(
        "Search the knowledge base"
    )

    update = asyncio.run(agent(state))

    result = update["agent_results"][0]

    assert update["active_agent"] == "research"
    assert update["hop_count"] == 1

    assert result["agent"] == "research"
    assert result["status"] == AgentStatus.FAILED
    assert result["content"] == ""
    assert result["error"] == "Semantic retrieval failed"
    assert (
        result["metadata"]["error_type"]
        == "RetrievalError"
    )

    assert update["errors"] == [
        "Semantic retrieval failed"
    ]


def test_research_agent_does_not_mutate_input_state() -> None:
    service = MagicMock(spec=RAGService)
    service.answer = AsyncMock(
        return_value=RAGAnswer(
            answer="Answer [S1].",
            sources=(make_source(),),
            model="fake-model",
        )
    )

    agent = ResearchAgent(service)

    state = create_initial_state(
        "Question",
        request_id="request-123",
    )

    asyncio.run(agent(state))

    assert state["active_agent"] is None
    assert state["agent_results"] == []
    assert state["sources"] == []
    assert state["errors"] == []
    assert state["hop_count"] == 0
