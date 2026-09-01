from typing import Annotated, Any

from pydantic import BaseModel, Field, StringConstraints

from orbyntiq.agents.state import AgentRoute

AgentQuery = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=20_000,
    ),
]

RequestId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=200,
    ),
]


class AgentExecuteRequest(BaseModel):
    query: AgentQuery
    request_id: RequestId | None = None
    conversation_id: RequestId | None = None
    max_hops: int = Field(
        default=8,
        ge=1,
        le=32,
    )


class AgentExecuteResponse(BaseModel):
    execution_id: str
    request_id: str
    route: AgentRoute
    route_reason: str | None
    final_response: str
    sources: list[dict[str, Any]]
    errors: list[str]
    hop_count: int
