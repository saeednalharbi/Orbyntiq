import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from mcp.server import MCPServer

from orbyntiq.agents.contracts import (
    AgentStatus,
    MCPToolDecision,
)
from orbyntiq.agents.mcp_agent import MCPAgent
from orbyntiq.agents.state import create_initial_state
from orbyntiq.services import LLMService


def make_math_server() -> MCPServer:
    server = MCPServer("test-mcp")

    @server.tool()
    def add_numbers(
        a: int,
        b: int,
    ) -> dict[str, int]:
        return {
            "result": a + b,
        }

    return server


def test_mcp_agent_discovers_and_executes_tool() -> None:
    service = MagicMock(spec=LLMService)
    service.chat_structured = AsyncMock(
        return_value=MCPToolDecision(
            tool_name="add_numbers",
            arguments={
                "a": 4,
                "b": 7,
            },
            reason="The user requested addition.",
        )
    )

    agent = MCPAgent(
        service,
        server=make_math_server(),
    )

    state = create_initial_state(
        "Add 4 and 7 using the available tool."
    )

    update = asyncio.run(agent(state))

    result = update["agent_results"][0]

    assert update["active_agent"] == "mcp"
    assert update["hop_count"] == 1

    assert result["agent"] == "mcp"
    assert result["status"] == AgentStatus.SUCCESS
    assert result["error"] is None

    payload = json.loads(result["content"])

    assert payload["result"] == 11

    assert (
        result["metadata"]["tool_name"]
        == "add_numbers"
    )
    assert result["metadata"]["arguments"] == {
        "a": 4,
        "b": 7,
    }


def test_mcp_agent_rejects_unknown_tool_selection() -> None:
    service = MagicMock(spec=LLMService)
    service.chat_structured = AsyncMock(
        return_value=MCPToolDecision(
            tool_name="does_not_exist",
            arguments={},
            reason="Incorrect tool selection.",
        )
    )

    agent = MCPAgent(
        service,
        server=make_math_server(),
    )

    state = create_initial_state(
        "Do something with a tool."
    )

    update = asyncio.run(agent(state))

    result = update["agent_results"][0]

    assert result["status"] == AgentStatus.FAILED
    assert (
        result["error"]
        == "MCP tool selection is invalid: does_not_exist"
    )

    assert update["errors"] == [
        "MCP tool selection is invalid: does_not_exist"
    ]


def test_mcp_agent_handles_tool_failure() -> None:
    server = MCPServer("failing-mcp")

    @server.tool()
    def explode() -> dict[str, str]:
        raise RuntimeError("boom")

    service = MagicMock(spec=LLMService)
    service.chat_structured = AsyncMock(
        return_value=MCPToolDecision(
            tool_name="explode",
            arguments={},
            reason="The requested operation requires this tool.",
        )
    )

    agent = MCPAgent(
        service,
        server=server,
    )

    state = create_initial_state(
        "Run the failing tool."
    )

    update = asyncio.run(agent(state))

    result = update["agent_results"][0]

    assert result["status"] == AgentStatus.FAILED
    assert result["error"]
    assert update["errors"]


def test_mcp_agent_propagates_sources() -> None:
    server = MCPServer("source-mcp")

    @server.tool()
    def grounded_lookup() -> dict[str, object]:
        return {
            "answer": "Grounded answer [S1].",
            "sources": [
                {
                    "citation": "S1",
                    "document_id": "doc-1",
                    "file_name": "policy.pdf",
                }
            ],
        }

    service = MagicMock(spec=LLMService)
    service.chat_structured = AsyncMock(
        return_value=MCPToolDecision(
            tool_name="grounded_lookup",
            arguments={},
            reason="Grounded lookup is required.",
        )
    )

    agent = MCPAgent(
        service,
        server=server,
    )

    state = create_initial_state(
        "Find the grounded answer."
    )

    update = asyncio.run(agent(state))

    assert len(update["sources"]) == 1
    assert update["sources"][0]["citation"] == "S1"
    assert (
        update["sources"][0]["file_name"]
        == "policy.pdf"
    )

    result = update["agent_results"][0]

    assert result["sources"] == update["sources"]


def test_mcp_agent_does_not_mutate_input_state() -> None:
    service = MagicMock(spec=LLMService)
    service.chat_structured = AsyncMock(
        return_value=MCPToolDecision(
            tool_name="add_numbers",
            arguments={
                "a": 1,
                "b": 2,
            },
            reason="Addition requested.",
        )
    )

    agent = MCPAgent(
        service,
        server=make_math_server(),
    )

    state = create_initial_state(
        "Add 1 and 2."
    )

    asyncio.run(agent(state))

    assert state["active_agent"] is None
    assert state["agent_results"] == []
    assert state["sources"] == []
    assert state["errors"] == []
    assert state["hop_count"] == 0
