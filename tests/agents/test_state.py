import pytest
from langchain_core.messages import HumanMessage

from orbyntiq.agents.state import create_initial_state


def test_create_initial_state() -> None:
    state = create_initial_state(
        "Explain vector databases",
        request_id="request-123",
        max_hops=6,
    )

    assert state["request_id"] == "request-123"
    assert state["user_query"] == "Explain vector databases"

    assert len(state["messages"]) == 1
    assert isinstance(state["messages"][0], HumanMessage)
    assert state["messages"][0].content == "Explain vector databases"

    assert state["route"] is None
    assert state["route_reason"] is None
    assert state["active_agent"] is None

    assert state["agent_results"] == []
    assert state["sources"] == []
    assert state["errors"] == []

    assert state["hop_count"] == 0
    assert state["max_hops"] == 6

    assert state["final_response"] is None


def test_create_initial_state_strips_query() -> None:
    state = create_initial_state("  Explain RAG  ")

    assert state["user_query"] == "Explain RAG"
    assert state["messages"][0].content == "Explain RAG"


def test_create_initial_state_generates_request_id() -> None:
    state = create_initial_state("Hello")

    assert state["request_id"]
    assert isinstance(state["request_id"], str)


def test_create_initial_state_rejects_empty_query() -> None:
    with pytest.raises(ValueError, match="user_query must not be empty"):
        create_initial_state("   ")


def test_create_initial_state_rejects_invalid_max_hops() -> None:
    with pytest.raises(ValueError, match="max_hops must be at least 1"):
        create_initial_state("Hello", max_hops=0)