import asyncio
from typing import Any

import pytest

from orbyntiq.agents.state import AgentState
from orbyntiq.persistence import (
    AgentExecution,
    WorkflowHistory,
)
from orbyntiq.services import (
    MultiAgentExecutionError,
    MultiAgentService,
)


class FakeExecutionRepository:
    def __init__(self) -> None:
        self.created: list[AgentExecution] = []
        self.replaced: list[AgentExecution] = []

    async def create(
        self,
        execution: AgentExecution,
    ) -> AgentExecution:
        self.created.append(
            execution
        )
        return execution

    async def replace(
        self,
        execution: AgentExecution,
    ) -> AgentExecution:
        self.replaced.append(
            execution
        )
        return execution


class FakeWorkflowRepository:
    def __init__(self) -> None:
        self.events: list[WorkflowHistory] = []

    async def create(
        self,
        event: WorkflowHistory,
    ) -> WorkflowHistory:
        self.events.append(
            event
        )
        return event


class SuccessfulGraph:
    async def ainvoke(
        self,
        input: AgentState,
    ) -> dict[str, Any]:
        return {
            "request_id":
                input["request_id"],
            "route": "general",
            "route_reason":
                "Direct response.",
            "final_response":
                "Embeddings are vectors.",
            "sources": [],
            "errors": [],
            "agent_results": [
                {
                    "agent": "general",
                    "status": "success",
                    "content":
                        "Embeddings are vectors.",
                    "metadata": {},
                    "sources": [],
                    "error": None,
                },
                {
                    "agent": "synthesizer",
                    "status": "success",
                    "content":
                        "Embeddings are vectors.",
                    "metadata": {},
                    "sources": [],
                    "error": None,
                },
            ],
            "hop_count": 3,
        }


def test_multi_agent_service_persists_execution() -> None:
    executions = FakeExecutionRepository()
    history = FakeWorkflowRepository()

    service = MultiAgentService(
        SuccessfulGraph(),
        execution_repository=executions,  # type: ignore[arg-type]
        workflow_repository=history,  # type: ignore[arg-type]
    )

    result = asyncio.run(
        service.execute(
            "Explain embeddings.",
            request_id="request-1",
            conversation_id="conversation-1",
        )
    )

    assert len(executions.created) == 1
    assert len(executions.replaced) == 1

    started = executions.created[0]
    completed = executions.replaced[0]

    assert started.id == result.execution_id
    assert started.status == "running"
    assert started.conversation_id == "conversation-1"
    assert started.started_at is not None

    assert completed.id == result.execution_id
    assert completed.status == "completed"
    assert completed.completed_at is not None
    assert completed.error is None

    assert (
        completed.output["final_response"]
        == "Embeddings are vectors."
    )

    assert completed.output["route"] == "general"

    assert [
        event.sequence
        for event in history.events
    ] == list(
        range(len(history.events))
    )

    assert [
        event.event_type
        for event in history.events
    ] == [
        "execution_started",
        "routing_completed",
        "agent_result",
        "agent_result",
        "execution_completed",
    ]

    assert (
        history.events[1].payload["route"]
        == "general"
    )

    assert (
        history.events[-1].payload["hop_count"]
        == 3
    )


def test_multi_agent_service_skips_persistence_without_conversation() -> None:
    executions = FakeExecutionRepository()
    history = FakeWorkflowRepository()

    service = MultiAgentService(
        SuccessfulGraph(),
        execution_repository=executions,  # type: ignore[arg-type]
        workflow_repository=history,  # type: ignore[arg-type]
    )

    asyncio.run(
        service.execute(
            "Explain embeddings."
        )
    )

    assert executions.created == []
    assert executions.replaced == []
    assert history.events == []


def test_multi_agent_service_persists_graph_failure() -> None:
    class FailingGraph:
        async def ainvoke(
            self,
            input: AgentState,
        ) -> dict[str, Any]:
            del input
            raise RuntimeError(
                "graph failed"
            )

    executions = FakeExecutionRepository()
    history = FakeWorkflowRepository()

    service = MultiAgentService(
        FailingGraph(),
        execution_repository=executions,  # type: ignore[arg-type]
        workflow_repository=history,  # type: ignore[arg-type]
    )

    with pytest.raises(
        MultiAgentExecutionError,
        match="graph execution failed",
    ):
        asyncio.run(
            service.execute(
                "Fail.",
                conversation_id="conversation-1",
            )
        )

    assert len(executions.created) == 1
    assert len(executions.replaced) == 1

    failed = executions.replaced[0]

    assert failed.status == "failed"
    assert failed.completed_at is not None
    assert (
        failed.error
        == "Multi-agent graph execution failed."
    )

    assert [
        event.event_type
        for event in history.events
    ] == [
        "execution_started",
        "execution_failed",
    ]


def test_multi_agent_service_rejects_partial_persistence_config() -> None:
    with pytest.raises(
        ValueError,
        match="must be configured together",
    ):
        MultiAgentService(
            SuccessfulGraph(),
            execution_repository=(
                FakeExecutionRepository()
            ),  # type: ignore[arg-type]
        )
