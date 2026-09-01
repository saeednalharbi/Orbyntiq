import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from orbyntiq.agents.contracts import RoutingDecision
from orbyntiq.agents.state import create_initial_state
from orbyntiq.agents.supervisor import (
    SUPERVISOR_SYSTEM_PROMPT,
    SupervisorAgent,
)
from orbyntiq.services import LLMService


@pytest.mark.parametrize(
    ("query", "route"),
    [
        (
            "What does the uploaded employee policy say about remote work?",
            "research",
        ),
        (
            "Use the available tool to calculate the project score.",
            "mcp",
        ),
        (
            "Explain what an embedding is.",
            "general",
        ),
    ],
)
def test_supervisor_routes_requests(
    query: str,
    route: str,
) -> None:
    service = MagicMock(spec=LLMService)
    service.chat_structured = AsyncMock(
        return_value=RoutingDecision(
            route=route,
            reason="Suitable capability",
        )
    )

    supervisor = SupervisorAgent(service)
    state = create_initial_state(query)

    update = asyncio.run(supervisor(state))

    assert update["route"] == route
    assert update["route_reason"] == "Suitable capability"
    assert update["active_agent"] == "supervisor"
    assert update["hop_count"] == 1

    service.chat_structured.assert_awaited_once_with(
        query,
        RoutingDecision,
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
    )


def test_supervisor_does_not_mutate_input_state() -> None:
    service = MagicMock(spec=LLMService)
    service.chat_structured = AsyncMock(
        return_value=RoutingDecision(
            route="general",
            reason="No specialized capability required",
        )
    )

    supervisor = SupervisorAgent(service)
    state = create_initial_state(
        "Explain transformers",
        request_id="request-123",
    )

    asyncio.run(supervisor(state))

    assert state["route"] is None
    assert state["route_reason"] is None
    assert state["active_agent"] is None
    assert state["hop_count"] == 0
