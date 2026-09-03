from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

ExecutionStatus = Literal[
    "queued",
    "running",
    "completed",
    "failed",
]


class ExecutionSummaryResponse(BaseModel):
    execution_id: str
    conversation_id: str
    agent_name: str
    status: ExecutionStatus

    request_id: str | None = None
    query: str | None = None

    route: str | None = None
    route_reason: str | None = None
    hop_count: int | None = None

    source_count: int = 0

    error: str | None = None

    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    duration_ms: float | None = None


class ExecutionListResponse(BaseModel):
    total: int
    count: int
    limit: int
    offset: int
    executions: list[ExecutionSummaryResponse]


class WorkflowEventResponse(BaseModel):
    id: str
    sequence: int
    event_type: str
    agent_name: str | None
    payload: dict[str, Any]
    created_at: datetime


class ExecutionDetailResponse(BaseModel):
    execution: ExecutionSummaryResponse
    input: dict[str, Any]
    output: dict[str, Any]
    events: list[WorkflowEventResponse]
