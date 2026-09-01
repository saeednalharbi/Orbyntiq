import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from orbyntiq.persistence import (
    AgentExecution,
    AgentExecutionRepository,
    RepositoryError,
)


def make_repository():
    collection = Mock()
    collection.replace_one = AsyncMock()

    database = Mock()
    database.__getitem__ = Mock(
        return_value=collection
    )

    repository = AgentExecutionRepository(
        database
    )

    return repository, collection


def test_agent_execution_repository_replace() -> None:
    repository, collection = make_repository()

    collection.replace_one.return_value = (
        SimpleNamespace(
            matched_count=1,
        )
    )

    execution = AgentExecution(
        id="execution-1",
        conversation_id="conversation-1",
        agent_name="multi_agent",
        status="completed",
        output={
            "final_response": "Done",
        },
    )

    result = asyncio.run(
        repository.replace(
            execution
        )
    )

    assert result == execution

    collection.replace_one.assert_awaited_once()

    filter_document = (
        collection.replace_one.await_args.args[0]
    )

    replacement_document = (
        collection.replace_one.await_args.args[1]
    )

    assert filter_document == {
        "_id": "execution-1"
    }

    assert (
        replacement_document["_id"]
        == "execution-1"
    )

    assert (
        replacement_document["status"]
        == "completed"
    )


def test_agent_execution_repository_replace_missing() -> None:
    repository, collection = make_repository()

    collection.replace_one.return_value = (
        SimpleNamespace(
            matched_count=0,
        )
    )

    execution = AgentExecution(
        id="execution-missing",
        conversation_id="conversation-1",
        agent_name="multi_agent",
    )

    with pytest.raises(
        RepositoryError,
        match="does not exist",
    ):
        asyncio.run(
            repository.replace(
                execution
            )
        )
