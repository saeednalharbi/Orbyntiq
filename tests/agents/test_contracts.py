import pytest
from pydantic import ValidationError

from orbyntiq.agents.contracts import (
    AgentResult,
    AgentStatus,
    MCPToolDecision,
    RoutingDecision,
)


def test_agent_result_success() -> None:
    result = AgentResult(
        agent="research",
        status=AgentStatus.SUCCESS,
        content="Retrieved relevant information.",
    )

    assert result.agent == "research"
    assert result.status == AgentStatus.SUCCESS
    assert result.content == "Retrieved relevant information."
    assert result.metadata == {}
    assert result.sources == []
    assert result.error is None


def test_agent_result_failure() -> None:
    result = AgentResult(
        agent="mcp",
        status=AgentStatus.FAILED,
        error="Tool execution failed",
    )

    assert result.status == AgentStatus.FAILED
    assert result.error == "Tool execution failed"


def test_agent_result_supports_metadata_and_sources() -> None:
    result = AgentResult(
        agent="research",
        status=AgentStatus.SUCCESS,
        content="Answer",
        metadata={"documents_retrieved": 2},
        sources=[
            {
                "document_id": "doc-1",
                "score": 0.91,
            }
        ],
    )

    assert result.metadata["documents_retrieved"] == 2
    assert result.sources[0]["document_id"] == "doc-1"


@pytest.mark.parametrize(
    "route",
    [
        "research",
        "mcp",
        "general",
    ],
)
def test_routing_decision_accepts_valid_routes(route: str) -> None:
    decision = RoutingDecision(
        route=route,
        reason="Suitable capability",
    )

    assert decision.route == route


def test_routing_decision_rejects_invalid_route() -> None:
    with pytest.raises(ValidationError):
        RoutingDecision(
            route="invalid-agent",
            reason="Invalid route",
        )


def test_routing_decision_requires_reason() -> None:
    with pytest.raises(ValidationError):
        RoutingDecision(
            route="general",
            reason="",
        )

def test_mcp_tool_decision_accepts_arguments() -> None:
    decision = MCPToolDecision(
        tool_name="search_knowledge",
        arguments={
            "query": "What is MCP?",
            "limit": 3,
        },
        reason="Knowledge search is required.",
    )

    assert decision.tool_name == "search_knowledge"
    assert decision.arguments["limit"] == 3


def test_mcp_tool_decision_rejects_empty_tool_name() -> None:
    with pytest.raises(ValidationError):
        MCPToolDecision(
            tool_name="",
            arguments={},
            reason="Invalid tool.",
        )
