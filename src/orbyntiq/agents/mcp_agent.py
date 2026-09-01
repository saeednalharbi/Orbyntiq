import json
from typing import Any

from mcp import Client, MCPError
from mcp.server import MCPServer
from mcp.types import TextContent, Tool

from orbyntiq.agents.contracts import (
    AgentResult,
    AgentStatus,
    MCPToolDecision,
)
from orbyntiq.agents.state import AgentState
from orbyntiq.mcp.server import mcp_server
from orbyntiq.services import LLMService

MCP_AGENT_SYSTEM_PROMPT = """
You are the MCP tool-selection agent inside Orbyntiq.

Your responsibility is to choose exactly one MCP tool that can satisfy the
user's request.

Rules:
- Select only a tool that appears in the supplied tool catalog.
- Never invent a tool name.
- Build arguments that follow the selected tool's input schema.
- Do not answer the user directly.
- Do not claim a tool succeeded before the application executes it.
- Return only the structured tool decision requested by the caller.
""".strip()


def _build_tool_catalog(tools: list[Tool]) -> str:
    catalog = [
        {
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": tool.input_schema,
        }
        for tool in tools
    ]

    return json.dumps(
        catalog,
        indent=2,
        sort_keys=True,
    )


def _extract_text(content: list[Any]) -> str:
    parts = [
        block.text
        for block in content
        if isinstance(block, TextContent)
        and block.text.strip()
    ]

    return "\n".join(parts).strip()


def _failure_update(
    state: AgentState,
    *,
    error: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = AgentResult(
        agent="mcp",
        status=AgentStatus.FAILED,
        error=error,
        metadata=metadata or {},
    )

    return {
        "active_agent": "mcp",
        "agent_results": [
            result.model_dump(mode="json"),
        ],
        "errors": [error],
        "hop_count": state["hop_count"] + 1,
    }


class MCPAgent:
    """Discover, select, and execute Orbyntiq MCP tools."""

    def __init__(
        self,
        llm_service: LLMService,
        *,
        server: MCPServer = mcp_server,
    ) -> None:
        self._llm_service = llm_service
        self._server = server

    async def _decide(
        self,
        state: AgentState,
        tools: list[Tool],
    ) -> MCPToolDecision:
        catalog = _build_tool_catalog(tools)

        prompt = (
            "Choose the best MCP tool for the user request.\n\n"
            f"User request:\n{state['user_query']}\n\n"
            f"Available MCP tools:\n{catalog}"
        )

        return await self._llm_service.chat_structured(
            prompt,
            MCPToolDecision,
            system_prompt=MCP_AGENT_SYSTEM_PROMPT,
        )

    async def __call__(
        self,
        state: AgentState,
    ) -> dict[str, Any]:
        """Discover and execute the MCP tool selected by the LLM."""

        try:
            async with Client(self._server) as client:
                tool_result = await client.list_tools()
                tools = tool_result.tools

                if not tools:
                    return _failure_update(
                        state,
                        error="No MCP tools are available.",
                    )

                decision = await self._decide(
                    state,
                    tools,
                )

                available_names = {
                    tool.name
                    for tool in tools
                }

                if decision.tool_name not in available_names:
                    return _failure_update(
                        state,
                        error=(
                            "MCP tool selection is invalid: "
                            f"{decision.tool_name}"
                        ),
                        metadata={
                            "selected_tool": decision.tool_name,
                            "available_tools": sorted(
                                available_names
                            ),
                        },
                    )

                result = await client.call_tool(
                    decision.tool_name,
                    decision.arguments,
                )

        except MCPError as exc:
            return _failure_update(
                state,
                error=str(exc),
                metadata={
                    "error_type": type(exc).__name__,
                },
            )

        if result.is_error:
            error_text = _extract_text(result.content)

            if not error_text:
                error_text = (
                    f"MCP tool {decision.tool_name} failed."
                )

            return _failure_update(
                state,
                error=error_text,
                metadata={
                    "tool_name": decision.tool_name,
                    "arguments": decision.arguments,
                    "reason": decision.reason,
                },
            )

        structured = result.structured_content

        if structured is not None:
            content = json.dumps(
                structured,
                ensure_ascii=False,
                sort_keys=True,
            )
        else:
            content = _extract_text(result.content)

        sources: list[dict[str, Any]] = []

        if isinstance(structured, dict):
            raw_sources = structured.get("sources")

            if isinstance(raw_sources, list):
                sources = [
                    source
                    for source in raw_sources
                    if isinstance(source, dict)
                ]

        agent_result = AgentResult(
            agent="mcp",
            status=AgentStatus.SUCCESS,
            content=content,
            metadata={
                "tool_name": decision.tool_name,
                "arguments": decision.arguments,
                "reason": decision.reason,
            },
            sources=sources,
        )

        return {
            "active_agent": "mcp",
            "agent_results": [
                agent_result.model_dump(mode="json"),
            ],
            "sources": sources,
            "hop_count": state["hop_count"] + 1,
        }
