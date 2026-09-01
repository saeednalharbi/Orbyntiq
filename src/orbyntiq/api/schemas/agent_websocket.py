from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StringConstraints

RequestId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=200,
    ),
]

AgentQuery = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=20_000,
    ),
]

ConversationId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=200,
    ),
]


class AgentExecuteWebSocketRequest(BaseModel):
    """Client request to execute the LangGraph multi-agent workflow."""

    type: Literal["agent_execute"] = "agent_execute"
    request_id: RequestId
    query: AgentQuery
    conversation_id: ConversationId | None = None
    max_hops: int = Field(
        default=8,
        ge=1,
    )


class AgentWorkflowEvent(BaseModel):
    """Workflow lifecycle event emitted during multi-agent execution."""

    type: Literal["agent_event"] = "agent_event"
    request_id: str
    execution_id: str
    sequence: int = Field(ge=0)
    event_type: str
    agent_name: str | None = None
    payload: dict[str, Any] = Field(
        default_factory=dict
    )
