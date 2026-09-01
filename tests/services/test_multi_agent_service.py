import asyncio
from typing import Any
from uuid import UUID

import pytest

from orbyntiq.agents.state import AgentState
from orbyntiq.services.multi_agent_service import (
    MultiAgentExecutionError,
    MultiAgentService,
)


class FakeGraph:
    def __init__(
        self,
        result: dict[str, Any],
    ) -> None:
        self.result = result
        self.last_state: AgentState | None = None

    async def ainvoke(
        self,
        input: AgentState,
    ) -> dict[str, Any]:
        self.last_state = input

        result = dict(self.result)

        result.setdefault(
            "request_id",
            input["request_id"],
        )

        return result


def make_success_result() -> dict[str, Any]:
    return {
        "route": "general",
        "route_reason": (
            "No specialized capability required."
        ),
        "final_response": (
            "An embedding is a numerical representation."
        ),
        "sources": [],
        "errors": [],
        "agent_results": [
            {
                "agent": "general",
                "status": "success",
                "content": (
                    "An embedding is a numerical representation."
                ),
            },
            {
                "agent": "synthesizer",
                "status": "success",
                "content": (
                    "An embedding is a numerical representation."
                ),
            },
        ],
        "hop_count": 3,
    }


def test_multi_agent_service_returns_structured_execution() -> None:
    graph = FakeGraph(
        make_success_result()
    )

    service = MultiAgentService(
        graph
    )

    execution = asyncio.run(
        service.execute(
            "Explain embeddings.",
            request_id="request-123",
        )
    )

    assert execution.request_id == "request-123"

    UUID(execution.execution_id)

    assert execution.route == "general"

    assert execution.route_reason == (
        "No specialized capability required."
    )

    assert execution.final_response == (
        "An embedding is a numerical representation."
    )

    assert execution.sources == ()
    assert execution.errors == ()

    assert len(
        execution.agent_results
    ) == 2

    assert execution.hop_count == 3

    assert graph.last_state is not None

    assert (
        graph.last_state["user_query"]
        == "Explain embeddings."
    )

    assert (
        graph.last_state["request_id"]
        == "request-123"
    )


def test_multi_agent_service_generates_request_id() -> None:
    graph = FakeGraph(
        make_success_result()
    )

    service = MultiAgentService(
        graph
    )

    execution = asyncio.run(
        service.execute(
            "Explain RAG."
        )
    )

    UUID(execution.request_id)
    UUID(execution.execution_id)

    assert (
        execution.execution_id
        != execution.request_id
    )


def test_multi_agent_service_passes_max_hops() -> None:
    graph = FakeGraph(
        make_success_result()
    )

    service = MultiAgentService(
        graph
    )

    asyncio.run(
        service.execute(
            "Explain MCP.",
            max_hops=5,
        )
    )

    assert graph.last_state is not None

    assert (
        graph.last_state["max_hops"]
        == 5
    )


def test_multi_agent_service_rejects_missing_final_response() -> None:
    graph = FakeGraph(
        {
            "route": "general",
            "final_response": "   ",
            "hop_count": 3,
        }
    )

    service = MultiAgentService(
        graph
    )

    with pytest.raises(
        MultiAgentExecutionError,
        match="no final response",
    ):
        asyncio.run(
            service.execute(
                "Test request"
            )
        )


def test_multi_agent_service_rejects_invalid_route() -> None:
    graph = FakeGraph(
        {
            "route": "invalid",
            "final_response": "Answer",
            "hop_count": 3,
        }
    )

    service = MultiAgentService(
        graph
    )

    with pytest.raises(
        MultiAgentExecutionError,
        match="invalid route",
    ):
        asyncio.run(
            service.execute(
                "Test request"
            )
        )


def test_multi_agent_service_wraps_graph_failure() -> None:
    class FailingGraph:
        async def ainvoke(
            self,
            input: AgentState,
        ) -> dict[str, Any]:
            del input

            raise RuntimeError(
                "graph exploded"
            )

    service = MultiAgentService(
        FailingGraph()
    )

    with pytest.raises(
        MultiAgentExecutionError,
        match="graph execution failed",
    ) as exc_info:
        asyncio.run(
            service.execute(
                "Test request"
            )
        )

    assert isinstance(
        exc_info.value.__cause__,
        RuntimeError,
    )
