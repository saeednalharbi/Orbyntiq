import asyncio
from unittest.mock import AsyncMock, MagicMock

from langchain_core.messages import AIMessage

from orbyntiq.agents.contracts import AgentResult, AgentStatus
from orbyntiq.agents.state import create_initial_state
from orbyntiq.agents.synthesizer import (
    SynthesizerAgent,
)
from orbyntiq.llm.models import LLMResponse
from orbyntiq.services import LLMService


def make_result(
    *,
    agent: str,
    content: str,
    status: AgentStatus = AgentStatus.SUCCESS,
    error: str | None = None,
    sources: list[dict] | None = None,
) -> dict:
    return AgentResult(
        agent=agent,
        status=status,
        content=content,
        error=error,
        sources=sources or [],
    ).model_dump(mode="json")


def test_synthesizer_passes_through_general_answer() -> None:
    service = MagicMock(spec=LLMService)
    service.chat = AsyncMock()

    agent = SynthesizerAgent(service)

    state = create_initial_state(
        "Explain embeddings."
    )

    state["route"] = "general"

    state["agent_results"].append(
        make_result(
            agent="general",
            content="An embedding is a numerical representation.",
        )
    )

    update = asyncio.run(agent(state))

    assert update["active_agent"] == "synthesizer"
    assert update["hop_count"] == 1

    assert (
        update["final_response"]
        == "An embedding is a numerical representation."
    )

    result = update["agent_results"][0]

    assert result["status"] == AgentStatus.SUCCESS
    assert result["metadata"]["mode"] == "passthrough"
    assert result["metadata"]["route"] == "general"

    assert isinstance(update["messages"][0], AIMessage)

    service.chat.assert_not_awaited()


def test_synthesizer_preserves_research_citations() -> None:
    service = MagicMock(spec=LLMService)
    service.chat = AsyncMock()

    agent = SynthesizerAgent(service)

    state = create_initial_state(
        "What is the retention period?"
    )

    state["route"] = "research"

    state["sources"].append(
        {
            "citation": "S1",
            "file_name": "policy.pdf",
            "document_id": "doc-1",
        }
    )

    state["agent_results"].append(
        make_result(
            agent="research",
            content="The retention period is 47 days [S1].",
            sources=state["sources"],
        )
    )

    update = asyncio.run(agent(state))

    assert (
        update["final_response"]
        == "The retention period is 47 days [S1]."
    )

    result = update["agent_results"][0]

    assert result["sources"] == state["sources"]
    assert result["metadata"]["mode"] == "passthrough"

    service.chat.assert_not_awaited()


def test_synthesizer_formats_mcp_output_safely() -> None:
    service = MagicMock(spec=LLMService)
    service.chat = AsyncMock()

    agent = SynthesizerAgent(service)

    state = create_initial_state(
        "Check the MCP platform status."
    )

    state["route"] = "mcp"

    state["agent_results"].append(
        make_result(
            agent="mcp",
            content=(
                '{"service":"orbyntiq-mcp",'
                '"status":"ok","protocol":"mcp"}'
            ),
        )
    )

    update = asyncio.run(agent(state))

    assert (
        update["final_response"]
        == "orbyntiq-mcp status is ok (protocol: mcp)."
    )

    result = update["agent_results"][0]

    assert result["status"] == AgentStatus.SUCCESS
    assert result["metadata"]["mode"] == "mcp_structured"
    assert result["metadata"]["route"] == "mcp"

    assert "orbyntiq-mcp" in update["final_response"]
    assert "[S1]" not in update["final_response"]

    service.chat.assert_not_awaited()

def test_synthesizer_handles_failed_upstream_agent() -> None:
    service = MagicMock(spec=LLMService)
    service.chat = AsyncMock()

    agent = SynthesizerAgent(service)

    state = create_initial_state(
        "Run a tool."
    )

    state["route"] = "mcp"

    state["agent_results"].append(
        make_result(
            agent="mcp",
            content="",
            status=AgentStatus.FAILED,
            error="Tool failed",
        )
    )

    update = asyncio.run(agent(state))

    result = update["agent_results"][0]

    assert result["status"] == AgentStatus.FAILED

    assert (
        update["final_response"]
        == (
            "I couldn't complete the request because the "
            "selected operation did not succeed."
        )
    )

    assert update["errors"] == [
        (
            "No successful agent result is available "
            "for synthesis."
        )
    ]

    service.chat.assert_not_awaited()


def test_synthesizer_handles_empty_llm_response() -> None:
    service = MagicMock(spec=LLMService)

    service.chat = AsyncMock(
        return_value=LLMResponse(
            content="   ",
            model="qwen3:4b-instruct",
        )
    )

    agent = SynthesizerAgent(service)

    state = create_initial_state(
        "Combine these execution results."
    )

    state["route"] = "mcp"

    state["agent_results"].extend(
        [
            make_result(
                agent="mcp",
                content='{"status":"ok"}',
            ),
            make_result(
                agent="mcp",
                content='{"protocol":"mcp"}',
            ),
        ]
    )

    update = asyncio.run(agent(state))

    result = update["agent_results"][0]

    assert result["status"] == AgentStatus.FAILED

    assert (
        result["error"]
        == "Synthesizer received an empty LLM response."
    )

    assert (
        update["final_response"]
        == "I couldn't produce a final response."
    )

    assert update["errors"] == [
        "Synthesizer received an empty LLM response."
    ]

    service.chat.assert_awaited_once()

def test_synthesizer_does_not_mutate_input_state() -> None:
    service = MagicMock(spec=LLMService)
    service.chat = AsyncMock()

    agent = SynthesizerAgent(service)

    state = create_initial_state(
        "Simple question."
    )

    state["route"] = "general"

    state["agent_results"].append(
        make_result(
            agent="general",
            content="Simple answer.",
        )
    )

    original_result_count = len(
        state["agent_results"]
    )

    original_message_count = len(
        state["messages"]
    )

    asyncio.run(agent(state))

    assert (
        len(state["agent_results"])
        == original_result_count
    )

    assert (
        len(state["messages"])
        == original_message_count
    )

    assert state["active_agent"] is None
    assert state["final_response"] is None
    assert state["hop_count"] == 0





