import asyncio
from typing import Any

import pytest

from orbyntiq.agents.contracts import (
    AgentResult,
    AgentStatus,
)
from orbyntiq.agents.graph import (
    GraphRoutingError,
    build_multi_agent_graph,
    select_route,
)
from orbyntiq.agents.state import (
    AgentState,
    create_initial_state,
)


@pytest.mark.parametrize(
    "route",
    [
        "research",
        "mcp",
        "general",
    ],
)
def test_select_route_accepts_valid_routes(
    route: str,
) -> None:
    state = create_initial_state(
        "Test request"
    )

    state["route"] = route  # type: ignore[assignment]

    assert select_route(state) == route


def test_select_route_rejects_missing_route() -> None:
    state = create_initial_state(
        "Test request"
    )

    with pytest.raises(
        GraphRoutingError,
        match="valid route",
    ):
        select_route(state)


@pytest.mark.parametrize(
    ("route", "expected_node"),
    [
        ("research", "research"),
        ("mcp", "mcp"),
        ("general", "general"),
    ],
)
def test_graph_routes_to_selected_agent(
    route: str,
    expected_node: str,
) -> None:
    events: list[str] = []

    async def supervisor(
        state: AgentState,
    ) -> dict[str, Any]:
        events.append("supervisor")

        return {
            "route": route,
            "route_reason": "Test routing decision",
            "active_agent": "supervisor",
            "hop_count": state["hop_count"] + 1,
        }

    def make_specialist(
        name: str,
    ):
        async def specialist(
            state: AgentState,
        ) -> dict[str, Any]:
            events.append(name)

            result = AgentResult(
                agent=name,
                status=AgentStatus.SUCCESS,
                content=f"{name} result",
            )

            return {
                "active_agent": name,
                "agent_results": [
                    result.model_dump(mode="json"),
                ],
                "hop_count": state["hop_count"] + 1,
            }

        return specialist

    async def synthesizer(
        state: AgentState,
    ) -> dict[str, Any]:
        events.append("synthesizer")

        return {
            "active_agent": "synthesizer",
            "final_response": (
                f"final response from {route}"
            ),
            "hop_count": state["hop_count"] + 1,
        }

    graph = build_multi_agent_graph(
        supervisor=supervisor,
        research=make_specialist("research"),
        mcp=make_specialist("mcp"),
        general=make_specialist("general"),
        synthesizer=synthesizer,
    )

    initial_state = create_initial_state(
        "Test graph request",
        request_id="graph-test",
    )

    result = asyncio.run(
        graph.ainvoke(initial_state)
    )

    assert events == [
        "supervisor",
        expected_node,
        "synthesizer",
    ]

    assert result["route"] == route

    assert (
        result["active_agent"]
        == "synthesizer"
    )

    assert (
        result["final_response"]
        == f"final response from {route}"
    )

    assert result["hop_count"] == 3

    assert len(
        result["agent_results"]
    ) == 1

    assert (
        result["agent_results"][0]["agent"]
        == expected_node
    )


def test_graph_preserves_initial_request() -> None:
    async def supervisor(
        state: AgentState,
    ) -> dict[str, Any]:
        return {
            "route": "general",
            "route_reason": "General request",
            "active_agent": "supervisor",
            "hop_count": state["hop_count"] + 1,
        }

    async def unused(
        state: AgentState,
    ) -> dict[str, Any]:
        return {
            "hop_count": state["hop_count"] + 1,
        }

    async def general(
        state: AgentState,
    ) -> dict[str, Any]:
        return {
            "active_agent": "general",
            "hop_count": state["hop_count"] + 1,
        }

    async def synthesizer(
        state: AgentState,
    ) -> dict[str, Any]:
        return {
            "active_agent": "synthesizer",
            "final_response": "Done",
            "hop_count": state["hop_count"] + 1,
        }

    graph = build_multi_agent_graph(
        supervisor=supervisor,
        research=unused,
        mcp=unused,
        general=general,
        synthesizer=synthesizer,
    )

    result = asyncio.run(
        graph.ainvoke(
            create_initial_state(
                "Explain vector embeddings",
                request_id="request-graph-123",
            )
        )
    )

    assert (
        result["user_query"]
        == "Explain vector embeddings"
    )

    assert (
        result["request_id"]
        == "request-graph-123"
    )

    assert result["final_response"] == "Done"
