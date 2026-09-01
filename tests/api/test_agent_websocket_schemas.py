import pytest
from pydantic import ValidationError

from orbyntiq.api.schemas.agent_websocket import (
    AgentExecuteWebSocketRequest,
    AgentWorkflowEvent,
)


def test_agent_execute_websocket_request() -> None:
    request = AgentExecuteWebSocketRequest(
        request_id="req-1",
        query="Explain embeddings.",
        conversation_id="conversation-1",
        max_hops=8,
    )

    assert request.type == "agent_execute"
    assert request.request_id == "req-1"
    assert request.query == "Explain embeddings."
    assert request.conversation_id == "conversation-1"
    assert request.max_hops == 8


def test_agent_execute_request_strips_query() -> None:
    request = AgentExecuteWebSocketRequest(
        request_id="req-1",
        query="  Explain embeddings.  ",
    )

    assert request.query == "Explain embeddings."


def test_agent_execute_request_rejects_empty_query() -> None:
    with pytest.raises(ValidationError):
        AgentExecuteWebSocketRequest(
            request_id="req-1",
            query="   ",
        )


def test_agent_workflow_event() -> None:
    event = AgentWorkflowEvent(
        request_id="req-1",
        execution_id="execution-1",
        sequence=2,
        event_type="agent_result",
        agent_name="general",
        payload={
            "status": "success",
        },
    )

    assert event.type == "agent_event"
    assert event.sequence == 2
    assert event.agent_name == "general"
    assert event.payload["status"] == "success"
