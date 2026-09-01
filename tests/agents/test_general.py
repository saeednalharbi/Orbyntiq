import asyncio
from unittest.mock import AsyncMock, MagicMock

from orbyntiq.agents.contracts import AgentStatus
from orbyntiq.agents.general import (
    GENERAL_AGENT_SYSTEM_PROMPT,
    GeneralAgent,
)
from orbyntiq.agents.state import create_initial_state
from orbyntiq.llm.models import LLMResponse
from orbyntiq.services import LLMService


def test_general_agent_returns_llm_answer() -> None:
    service = MagicMock(spec=LLMService)
    service.chat = AsyncMock(
        return_value=LLMResponse(
            content="An embedding is a numerical representation.",
            model="qwen3:4b-instruct",
            prompt_tokens=20,
            completion_tokens=10,
        )
    )

    agent = GeneralAgent(service)

    state = create_initial_state(
        "Explain what an embedding is."
    )

    update = asyncio.run(agent(state))

    result = update["agent_results"][0]

    assert update["active_agent"] == "general"
    assert update["hop_count"] == 1

    assert result["agent"] == "general"
    assert result["status"] == AgentStatus.SUCCESS
    assert (
        result["content"]
        == "An embedding is a numerical representation."
    )

    assert (
        result["metadata"]["model"]
        == "qwen3:4b-instruct"
    )
    assert result["metadata"]["prompt_tokens"] == 20
    assert result["metadata"]["completion_tokens"] == 10
    assert result["error"] is None

    service.chat.assert_awaited_once_with(
        "Explain what an embedding is.",
        system_prompt=GENERAL_AGENT_SYSTEM_PROMPT,
    )


def test_general_agent_handles_empty_response() -> None:
    service = MagicMock(spec=LLMService)
    service.chat = AsyncMock(
        return_value=LLMResponse(
            content="   ",
            model="qwen3:4b-instruct",
        )
    )

    agent = GeneralAgent(service)

    state = create_initial_state(
        "Explain transformers."
    )

    update = asyncio.run(agent(state))

    result = update["agent_results"][0]

    assert result["status"] == AgentStatus.FAILED
    assert (
        result["error"]
        == "General agent received an empty LLM response."
    )

    assert update["errors"] == [
        "General agent received an empty LLM response."
    ]

    assert update["active_agent"] == "general"
    assert update["hop_count"] == 1


def test_general_agent_does_not_mutate_input_state() -> None:
    service = MagicMock(spec=LLMService)
    service.chat = AsyncMock(
        return_value=LLMResponse(
            content="Direct answer.",
            model="fake-model",
        )
    )

    agent = GeneralAgent(service)

    state = create_initial_state(
        "Simple question",
        request_id="request-123",
    )

    asyncio.run(agent(state))

    assert state["active_agent"] is None
    assert state["agent_results"] == []
    assert state["sources"] == []
    assert state["errors"] == []
    assert state["hop_count"] == 0
