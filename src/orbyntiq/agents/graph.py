from collections.abc import Awaitable, Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from orbyntiq.agents.state import (
    AgentRoute,
    AgentState,
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


def build_multi_agent_graph(
    *,
    supervisor: AgentNode,
    research: AgentNode,
    mcp: AgentNode,
    general: AgentNode,
    synthesizer: AgentNode,
) -> Any:
    """Build and compile the Orbyntiq multi-agent LangGraph."""

    graph = StateGraph(AgentState)

    graph.add_node(
        "supervisor",
        supervisor,
    )

    graph.add_node(
        "research",
        research,
    )

    graph.add_node(
        "mcp",
        mcp,
    )

    graph.add_node(
        "general",
        general,
    )

    graph.add_node(
        "synthesizer",
        synthesizer,
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
