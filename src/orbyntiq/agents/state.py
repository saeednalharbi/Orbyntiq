from operator import add
from typing import Annotated, Any, Literal, TypedDict
from uuid import uuid4

from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph import add_messages

AgentName = Literal[
    "supervisor",
    "research",
    "mcp",
    "general",
    "synthesizer",
]

AgentRoute = Literal[
    "research",
    "mcp",
    "general",
]


class AgentState(TypedDict):
    """Shared state passed between Orbyntiq LangGraph agents."""

    request_id: str
    user_query: str

    messages: Annotated[list[AnyMessage], add_messages]

    route: AgentRoute | None
    route_reason: str | None
    active_agent: AgentName | None

    agent_results: Annotated[list[dict[str, Any]], add]
    sources: Annotated[list[dict[str, Any]], add]
    errors: Annotated[list[str], add]

    hop_count: int
    max_hops: int

    final_response: str | None


def create_initial_state(
    user_query: str,
    *,
    request_id: str | None = None,
    max_hops: int = 8,
) -> AgentState:
    """Create a clean initial state for a multi-agent execution."""

    query = user_query.strip()

    if not query:
        raise ValueError("user_query must not be empty")

    if max_hops < 1:
        raise ValueError("max_hops must be at least 1")

    return AgentState(
        request_id=request_id or str(uuid4()),
        user_query=query,
        messages=[HumanMessage(content=query)],
        route=None,
        route_reason=None,
        active_agent=None,
        agent_results=[],
        sources=[],
        errors=[],
        hop_count=0,
        max_hops=max_hops,
        final_response=None,
    )