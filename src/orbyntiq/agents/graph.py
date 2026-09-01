from collections.abc import Awaitable, Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from orbyntiq.agents.state import (
    AgentRoute,
    AgentState,
)
from orbyntiq.observability.spans import (
    mark_span_error,
    traced_span,
)

AgentNode = Callable[
    [AgentState],
    Awaitable[dict[str, Any]],
]


class GraphRoutingError(RuntimeError):
    """Raised when the supervisor does not produce a valid route."""


def select_route(
    state: AgentState,
) -> AgentRoute:
    """Select the specialist node requested by the supervisor."""

    route = state["route"]

    if route not in {
        "research",
        "mcp",
        "general",
    }:
        raise GraphRoutingError(
            "Supervisor did not produce a valid route."
        )

    return route


def _agent_result_status(
    update: dict[str, Any],
    agent_name: str,
) -> str:
    results = update.get(
        "agent_results"
    )

    if not isinstance(
        results,
        list,
    ):
        return "success"

    for result in reversed(results):
        if not isinstance(
            result,
            dict,
        ):
            continue

        if (
            result.get("agent")
            == agent_name
        ):
            status = result.get(
                "status"
            )

            if status in {
                "success",
                "failed",
            }:
                return str(status)

    return "success"


def _instrument_agent_node(
    agent_name: str,
    node: AgentNode,
) -> AgentNode:
    async def traced_node(
        state: AgentState,
    ) -> dict[str, Any]:
        with traced_span(
            f"agent.{agent_name}",
            tracer_name="orbyntiq.agents",
            attributes={
                "gen_ai.operation.name": "invoke_agent",
                "gen_ai.agent.name": agent_name,
                "orbyntiq.agent.name": agent_name,
            },
        ) as span:
            update = await node(
                state
            )

            status = _agent_result_status(
                update,
                agent_name,
            )

            span.set_attribute(
                "orbyntiq.agent.status",
                status,
            )

            if status == "failed":
                mark_span_error(
                    span,
                    "AgentExecutionFailed",
                )

            route = update.get(
                "route"
            )

            if (
                agent_name == "supervisor"
                and route
                in {
                    "research",
                    "mcp",
                    "general",
                }
            ):
                span.set_attribute(
                    "orbyntiq.agent.route",
                    str(route),
                )

            return update

    return traced_node


def build_multi_agent_graph(
    *,
    supervisor: AgentNode,
    research: AgentNode,
    mcp: AgentNode,
    general: AgentNode,
    synthesizer: AgentNode,
) -> Any:
    """Build and compile the Orbyntiq multi-agent LangGraph."""

    graph = StateGraph(
        AgentState
    )

    graph.add_node(
        "supervisor",
        _instrument_agent_node(
            "supervisor",
            supervisor,
        ),
    )

    graph.add_node(
        "research",
        _instrument_agent_node(
            "research",
            research,
        ),
    )

    graph.add_node(
        "mcp",
        _instrument_agent_node(
            "mcp",
            mcp,
        ),
    )

    graph.add_node(
        "general",
        _instrument_agent_node(
            "general",
            general,
        ),
    )

    graph.add_node(
        "synthesizer",
        _instrument_agent_node(
            "synthesizer",
            synthesizer,
        ),
    )

    graph.add_edge(
        START,
        "supervisor",
    )

    graph.add_conditional_edges(
        "supervisor",
        select_route,
        {
            "research": "research",
            "mcp": "mcp",
            "general": "general",
        },
    )

    graph.add_edge(
        "research",
        "synthesizer",
    )

    graph.add_edge(
        "mcp",
        "synthesizer",
    )

    graph.add_edge(
        "general",
        "synthesizer",
    )

    graph.add_edge(
        "synthesizer",
        END,
    )

    return graph.compile()
