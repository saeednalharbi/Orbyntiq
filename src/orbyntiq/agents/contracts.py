from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from orbyntiq.agents.state import AgentRoute


class AgentStatus(StrEnum):
    """Execution status returned by an Orbyntiq agent."""

    SUCCESS = "success"
    FAILED = "failed"


class AgentResult(BaseModel):
    """Standard result contract returned by an agent."""

    agent: str = Field(min_length=1)
    status: AgentStatus
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class RoutingDecision(BaseModel):
    """Structured routing decision produced by the supervisor."""

    route: AgentRoute
    reason: str = Field(min_length=1)


class MCPToolDecision(BaseModel):
    """Structured MCP tool selection produced by the LLM."""

    tool_name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(min_length=1)
