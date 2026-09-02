import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, cast
from uuid import uuid4

from orbyntiq.agents.state import (
    AgentRoute,
    AgentState,
    create_initial_state,
)
from orbyntiq.persistence import (
    AgentExecution,
    AgentExecutionRepository,
    RepositoryError,
    WorkflowHistory,
    WorkflowHistoryRepository,
)


class MultiAgentUnavailableError(RuntimeError):
    """Raised when the multi-agent runtime is unavailable."""


class MultiAgentExecutionError(RuntimeError):
    """Raised when a multi-agent graph execution cannot complete."""


class MultiAgentGraph(Protocol):
    """Minimal graph contract required by MultiAgentService."""

    async def ainvoke(
        self,
        input: AgentState,
    ) -> dict[str, Any]: ...


MultiAgentEventCallback = Callable[
    [dict[str, Any]],
    Awaitable[None],
]


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
        *,
        execution_repository: AgentExecutionRepository | None = None,
        workflow_repository: WorkflowHistoryRepository | None = None,
    ) -> None:
        if (execution_repository is None) != (workflow_repository is None):
            raise ValueError(
                "execution_repository and workflow_repository must be configured together"
            )

        self._graph = graph
        self._execution_repository = execution_repository
        self._workflow_repository = workflow_repository

    def _persistence_enabled(
        self,
        conversation_id: str | None,
    ) -> bool:
        return (
            conversation_id is not None
            and self._execution_repository is not None
            and self._workflow_repository is not None
        )

    async def _emit_event(
        self,
        callback: MultiAgentEventCallback | None,
        *,
        execution_id: str,
        request_id: str,
        sequence: int,
        event_type: str,
        agent_name: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Publish an optional best-effort execution event."""

        if callback is None:
            return

        event = {
            "request_id": request_id,
            "execution_id": execution_id,
            "sequence": sequence,
            "event_type": event_type,
            "agent_name": agent_name,
            "payload": payload or {},
        }

        try:
            await callback(event)
        except Exception:
            # Event delivery must never corrupt the underlying
            # multi-agent execution or MongoDB persistence.
            return

    async def _create_workflow_event(
        self,
        *,
        execution_id: str,
        conversation_id: str,
        sequence: int,
        event_type: str,
        agent_name: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if self._workflow_repository is None:
            return

        await self._workflow_repository.create(
            WorkflowHistory(
                execution_id=execution_id,
                conversation_id=conversation_id,
                sequence=sequence,
                event_type=event_type,
                agent_name=agent_name,
                payload=payload or {},
            )
        )

    async def _persist_failure(
        self,
        execution: AgentExecution,
        *,
        sequence: int,
        error: str,
    ) -> None:
        if self._execution_repository is None or self._workflow_repository is None:
            return

        await self._create_workflow_event(
            execution_id=execution.id,
            conversation_id=execution.conversation_id,
            sequence=sequence,
            event_type="execution_failed",
            payload={
                "error": error,
            },
        )

        failed_execution = execution.model_copy(
            update={
                "status": "failed",
                "error": error,
                "completed_at": datetime.now(UTC),
            }
        )

        await self._execution_repository.replace(failed_execution)

    async def execute(
        self,
        user_query: str,
        *,
        request_id: str | None = None,
        conversation_id: str | None = None,
        max_hops: int = 8,
        event_callback: MultiAgentEventCallback | None = None,
    ) -> MultiAgentExecution:
        """Execute one multi-agent request."""

        execution_id = str(uuid4())

        initial_state = create_initial_state(
            user_query,
            request_id=request_id,
            max_hops=max_hops,
        )

        persisted_execution: AgentExecution | None = None
        next_sequence = 0

        if self._persistence_enabled(conversation_id):
            assert conversation_id is not None
            assert self._execution_repository is not None

            persisted_execution = AgentExecution(
                id=execution_id,
                conversation_id=conversation_id,
                agent_name="multi_agent",
                status="running",
                input={
                    "user_query": initial_state["user_query"],
                    "request_id": initial_state["request_id"],
                    "max_hops": max_hops,
                },
                started_at=datetime.now(UTC),
            )

            try:
                await self._execution_repository.create(persisted_execution)

                await self._create_workflow_event(
                    execution_id=execution_id,
                    conversation_id=conversation_id,
                    sequence=next_sequence,
                    event_type="execution_started",
                    agent_name="supervisor",
                    payload={
                        "request_id": initial_state["request_id"],
                        "user_query": initial_state["user_query"],
                    },
                )

            except RepositoryError as exc:
                raise MultiAgentExecutionError(
                    "Failed to persist multi-agent execution start."
                ) from exc

        await self._emit_event(
            event_callback,
            execution_id=execution_id,
            request_id=initial_state["request_id"],
            sequence=next_sequence,
            event_type="execution_started",
            agent_name="supervisor",
            payload={
                "request_id": initial_state["request_id"],
                "user_query": initial_state["user_query"],
            },
        )

        next_sequence += 1

        callback_sequence = 1
        live_callback_stream = False

        try:
            stream_method = getattr(
                self._graph,
                "astream",
                None,
            )

            if event_callback is not None and callable(stream_method):
                live_callback_stream = True

                result: dict[str, Any] | None = None
                route_event_emitted = False
                emitted_agent_results = 0

                async for streamed_state in stream_method(
                    initial_state,
                    stream_mode="values",
                ):
                    if not isinstance(
                        streamed_state,
                        dict,
                    ):
                        continue

                    result = dict(streamed_state)

                    streamed_route = result.get("route")

                    if not route_event_emitted and streamed_route in {
                        "research",
                        "mcp",
                        "general",
                    }:
                        route_reason_value = result.get("route_reason")

                        route_reason = (
                            None if route_reason_value is None else str(route_reason_value)
                        )

                        await self._emit_event(
                            event_callback,
                            execution_id=execution_id,
                            request_id=(initial_state["request_id"]),
                            sequence=(callback_sequence),
                            event_type=("routing_completed"),
                            agent_name="supervisor",
                            payload={
                                "route": streamed_route,
                                "route_reason": route_reason,
                            },
                        )

                        callback_sequence += 1
                        route_event_emitted = True

                        await self._emit_event(
                            event_callback,
                            execution_id=execution_id,
                            request_id=(initial_state["request_id"]),
                            sequence=(callback_sequence),
                            event_type=("agent_started"),
                            agent_name=str(streamed_route),
                            payload={
                                "route": streamed_route,
                            },
                        )

                        callback_sequence += 1

                    raw_agent_results = result.get(
                        "agent_results",
                        [],
                    )

                    if isinstance(
                        raw_agent_results,
                        list,
                    ):
                        current_results = [
                            dict(item)
                            for item in raw_agent_results
                            if isinstance(
                                item,
                                dict,
                            )
                        ]

                        for agent_result in current_results[emitted_agent_results:]:
                            agent_name_value = agent_result.get("agent")

                            agent_name = None if agent_name_value is None else str(agent_name_value)

                            await self._emit_event(
                                event_callback,
                                execution_id=(execution_id),
                                request_id=(initial_state["request_id"]),
                                sequence=(callback_sequence),
                                event_type=("agent_result"),
                                agent_name=(agent_name),
                                payload=(agent_result),
                            )

                            callback_sequence += 1

                        emitted_agent_results = len(current_results)

                if result is None:
                    raise RuntimeError("Multi-agent graph stream returned no state.")

            else:
                result = await self._graph.ainvoke(initial_state)
        except asyncio.CancelledError:
            error = "Multi-agent execution cancelled."

            if persisted_execution is not None:
                try:
                    await self._persist_failure(
                        persisted_execution,
                        sequence=next_sequence,
                        error=error,
                    )
                except RepositoryError:
                    pass

            await self._emit_event(
                event_callback,
                execution_id=execution_id,
                request_id=initial_state["request_id"],
                sequence=callback_sequence,
                event_type="execution_failed",
                payload={
                    "error": error,
                },
            )

            raise

        except Exception as exc:
            error = "Multi-agent graph execution failed."

            if persisted_execution is not None:
                try:
                    await self._persist_failure(
                        persisted_execution,
                        sequence=next_sequence,
                        error=error,
                    )
                except RepositoryError:
                    pass

            await self._emit_event(
                event_callback,
                execution_id=execution_id,
                request_id=initial_state["request_id"],
                sequence=callback_sequence,
                event_type="execution_failed",
                payload={
                    "error": error,
                },
            )

            raise MultiAgentExecutionError(error) from exc

        route = result.get("route")

        if route not in {
            "research",
            "mcp",
            "general",
        }:
            error = "Multi-agent execution returned an invalid route."

            if persisted_execution is not None:
                try:
                    await self._persist_failure(
                        persisted_execution,
                        sequence=next_sequence,
                        error=error,
                    )
                except RepositoryError:
                    pass

            await self._emit_event(
                event_callback,
                execution_id=execution_id,
                request_id=initial_state["request_id"],
                sequence=next_sequence,
                event_type="execution_failed",
                payload={
                    "error": error,
                },
            )

            raise MultiAgentExecutionError(error)

        final_response = str(
            result.get(
                "final_response",
                "",
            )
        ).strip()

        if not final_response:
            error = "Multi-agent execution returned no final response."

            if persisted_execution is not None:
                try:
                    await self._persist_failure(
                        persisted_execution,
                        sequence=next_sequence,
                        error=error,
                    )
                except RepositoryError:
                    pass

            await self._emit_event(
                event_callback,
                execution_id=execution_id,
                request_id=initial_state["request_id"],
                sequence=next_sequence,
                event_type="execution_failed",
                payload={
                    "error": error,
                },
            )

            raise MultiAgentExecutionError(error)

        resolved_request_id = str(
            result.get(
                "request_id",
                initial_state["request_id"],
            )
        )

        route_reason_value = result.get("route_reason")

        route_reason = None if route_reason_value is None else str(route_reason_value)

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

        execution = MultiAgentExecution(
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

        if persisted_execution is not None:
            assert self._execution_repository is not None

            try:
                await self._create_workflow_event(
                    execution_id=execution_id,
                    conversation_id=(persisted_execution.conversation_id),
                    sequence=next_sequence,
                    event_type="routing_completed",
                    agent_name="supervisor",
                    payload={
                        "route": execution.route,
                        "route_reason": execution.route_reason,
                    },
                )

                next_sequence += 1

                for agent_result in agent_results:
                    agent_name_value = agent_result.get("agent")

                    agent_name = None if agent_name_value is None else str(agent_name_value)

                    await self._create_workflow_event(
                        execution_id=execution_id,
                        conversation_id=(persisted_execution.conversation_id),
                        sequence=next_sequence,
                        event_type="agent_result",
                        agent_name=agent_name,
                        payload=agent_result,
                    )

                    next_sequence += 1

                await self._create_workflow_event(
                    execution_id=execution_id,
                    conversation_id=(persisted_execution.conversation_id),
                    sequence=next_sequence,
                    event_type="execution_completed",
                    agent_name="synthesizer",
                    payload={
                        "route": execution.route,
                        "hop_count": execution.hop_count,
                        "final_response": execution.final_response,
                        "errors": list(execution.errors),
                        "sources": list(execution.sources),
                    },
                )

                completed_execution = persisted_execution.model_copy(
                    update={
                        "status": "completed",
                        "output": {
                            "request_id": execution.request_id,
                            "route": execution.route,
                            "route_reason": execution.route_reason,
                            "final_response": execution.final_response,
                            "sources": list(execution.sources),
                            "errors": list(execution.errors),
                            "agent_results": list(execution.agent_results),
                            "hop_count": execution.hop_count,
                        },
                        "completed_at": datetime.now(UTC),
                    }
                )

                await self._execution_repository.replace(completed_execution)

            except RepositoryError as exc:
                raise MultiAgentExecutionError(
                    "Failed to persist multi-agent execution result."
                ) from exc

        event_sequence = callback_sequence

        if not live_callback_stream:
            event_sequence = 1

            await self._emit_event(
                event_callback,
                execution_id=(execution.execution_id),
                request_id=(execution.request_id),
                sequence=event_sequence,
                event_type=("routing_completed"),
                agent_name="supervisor",
                payload={
                    "route": execution.route,
                    "route_reason": execution.route_reason,
                },
            )

            event_sequence += 1

            for agent_result in execution.agent_results:
                agent_name_value = agent_result.get("agent")

                agent_name = None if agent_name_value is None else str(agent_name_value)

                await self._emit_event(
                    event_callback,
                    execution_id=(execution.execution_id),
                    request_id=(execution.request_id),
                    sequence=(event_sequence),
                    event_type=("agent_result"),
                    agent_name=(agent_name),
                    payload=(agent_result),
                )

                event_sequence += 1

        await self._emit_event(
            event_callback,
            execution_id=execution.execution_id,
            request_id=execution.request_id,
            sequence=event_sequence,
            event_type="execution_completed",
            agent_name="synthesizer",
            payload={
                "route": execution.route,
                "hop_count": execution.hop_count,
                "final_response": execution.final_response,
                "errors": list(execution.errors),
                "sources": list(execution.sources),
            },
        )

        return execution
