import asyncio
from uuid import uuid4

import pytest

from orbyntiq.core.config import get_settings
from orbyntiq.core.mongodb import (
    MongoDBUnavailableError,
    close_mongodb_client,
    create_mongodb_client,
    verify_mongodb_connection,
)
from orbyntiq.core.mongodb_schema import (
    AGENT_EXECUTIONS_COLLECTION,
    WORKFLOW_HISTORY_COLLECTION,
    ensure_mongodb_schema,
)
from orbyntiq.persistence import (
    AgentExecution,
    AgentExecutionRepository,
    RepositoryConflictError,
    WorkflowHistory,
    WorkflowHistoryRepository,
)


def test_agent_execution_and_workflow_history_round_trip() -> None:
    async def scenario() -> None:
        settings = get_settings()
        client = create_mongodb_client(settings)
        database = client[settings.mongodb_database]

        execution_id: str | None = None

        try:
            try:
                await verify_mongodb_connection(
                    client
                )
            except MongoDBUnavailableError:
                pytest.skip(
                    "MongoDB is not available"
                )

            await ensure_mongodb_schema(database)

            executions = AgentExecutionRepository(
                database
            )
            history = WorkflowHistoryRepository(
                database
            )

            marker = f"phase06-{uuid4()}"

            execution = AgentExecution(
                conversation_id=marker,
                agent_name="research",
                status="running",
                input={
                    "query": "Orbyntiq architecture"
                },
            )

            execution_id = execution.id

            await executions.create(execution)

            first_event = WorkflowHistory(
                execution_id=execution.id,
                conversation_id=marker,
                sequence=0,
                event_type="execution_started",
                agent_name="research",
            )

            second_event = WorkflowHistory(
                execution_id=execution.id,
                conversation_id=marker,
                sequence=1,
                event_type="tool_completed",
                agent_name="research",
                payload={
                    "tool": "retrieval"
                },
            )

            await history.create(first_event)
            await history.create(second_event)

            stored_execution = await executions.get(
                execution.id
            )

            assert stored_execution == execution

            stored_history = (
                await history.list_for_execution(
                    execution.id
                )
            )

            assert stored_history == [
                first_event,
                second_event,
            ]

            duplicate = WorkflowHistory(
                execution_id=execution.id,
                conversation_id=marker,
                sequence=1,
                event_type="duplicate",
            )

            with pytest.raises(
                RepositoryConflictError
            ):
                await history.create(duplicate)

        finally:
            if execution_id is not None:
                await database[
                    WORKFLOW_HISTORY_COLLECTION
                ].delete_many(
                    {
                        "execution_id":
                            execution_id
                    }
                )

                await database[
                    AGENT_EXECUTIONS_COLLECTION
                ].delete_many(
                    {"_id": execution_id}
                )

            await close_mongodb_client(client)

    asyncio.run(scenario())