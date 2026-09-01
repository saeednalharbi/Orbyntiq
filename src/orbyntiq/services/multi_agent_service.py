from dataclasses import dataclass
from typing import Any, Protocol, cast
from uuid import uuid4

from orbyntiq.agents.state import (
    AgentRoute,
    AgentState,
    create_initial_state,
)


class MultiAgentExecutionError(RuntimeError):
    """Raised when a multi-agent graph execution cannot complete."""


class MultiAgentGraph(Protocol):
    """Minimal graph contract required by MultiAgentService."""

    async def ainvoke(
        self,
        input: AgentState,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class MultiAgentExecution:
    """Structured result returned by a multi-agent execution."""

    execution_id: str
    request_id: str
    route: AgentRoute
    route_reason: str | None
    final_response: str
    sources: tuple[dict[str, Any], ...]
    errors: tuple[str, ...]
    agent_results: tuple[dict[str, Any], ...]
    hop_count: int


class MultiAgentService:
    """Application service for executing the Orbyntiq agent graph."""

    def __init__(
        self,
        graph: MultiAgentGraph,
    ) -> None:
        self._graph = graph

    async def execute(
        self,
        user_query: str,
        *,
        request_id: str | None = None,
        max_hops: int = 8,
    ) -> MultiAgentExecution:
        """Execute one multi-agent request."""

        execution_id = str(uuid4())

        initial_state = create_initial_state(
            user_query,
            request_id=request_id,
            max_hops=max_hops,
        )

        try:
            result = await self._graph.ainvoke(
                initial_state
            )
        except Exception as exc:
            raise MultiAgentExecutionError(
                "Multi-agent graph execution failed."
            ) from exc

        route = result.get("route")

        if route not in {
            "research",
            "mcp",
            "general",
        }:
            raise MultiAgentExecutionError(
                "Multi-agent execution returned an invalid route."
            )

        final_response = str(
            result.get(
                "final_response",
                "",
            )
        ).strip()

        if not final_response:
            raise MultiAgentExecutionError(
                "Multi-agent execution returned no final response."
            )

        resolved_request_id = str(
            result.get(
                "request_id",
                initial_state["request_id"],
            )
        )

        route_reason_value = result.get(
            "route_reason"
        )

        route_reason = (
            None
            if route_reason_value is None
            else str(route_reason_value)
        )

        sources = tuple(
            dict(source)
            for source in result.get(
                "sources",
                [],
            )
            if isinstance(source, dict)
        )

        errors = tuple(
            str(error)
            for error in result.get(
                "errors",
                [],
            )
        )

        agent_results = tuple(
            dict(agent_result)
            for agent_result in result.get(
                "agent_results",
                [],
            )
            if isinstance(agent_result, dict)
        )

        return MultiAgentExecution(
            execution_id=execution_id,
            request_id=resolved_request_id,
            route=cast(
                AgentRoute,
                route,
            ),
            route_reason=route_reason,
            final_response=final_response,
            sources=sources,
            errors=errors,
            agent_results=agent_results,
            hop_count=int(
                result.get(
                    "hop_count",
                    0,
                )
            ),
        )
