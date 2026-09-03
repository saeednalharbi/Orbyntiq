from datetime import datetime
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from pymongo.asynchronous.database import AsyncDatabase

from orbyntiq.api.dependencies import (
    get_mongodb_database,
)
from orbyntiq.api.schemas.executions import (
    ExecutionDetailResponse,
    ExecutionListResponse,
    ExecutionSummaryResponse,
    WorkflowEventResponse,
)
from orbyntiq.core.mongodb import MongoDocument
from orbyntiq.persistence import (
    AgentExecution,
    AgentExecutionRepository,
    RepositoryError,
    WorkflowHistoryRepository,
)

router = APIRouter(
    prefix="/api/v1/executions",
    tags=["executions"],
)


def _optional_string(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    return text or None


def _optional_int(
    value: Any,
) -> int | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value

    try:
        return int(value)
    except (
        TypeError,
        ValueError,
    ):
        return None


def _duration_ms(
    started_at: datetime | None,
    completed_at: datetime | None,
) -> float | None:
    if started_at is None or completed_at is None:
        return None

    duration = (completed_at - started_at).total_seconds() * 1000

    return max(
        0.0,
        round(duration, 2),
    )


def _source_count(
    output: dict[str, Any],
) -> int:
    sources = output.get("sources")

    if not isinstance(sources, list):
        return 0

    return len(sources)


def _execution_summary(
    execution: AgentExecution,
) -> ExecutionSummaryResponse:
    input_data = execution.input
    output_data = execution.output

    request_id = _optional_string(output_data.get("request_id")) or _optional_string(
        input_data.get("request_id")
    )

    return ExecutionSummaryResponse(
        execution_id=execution.id,
        conversation_id=(execution.conversation_id),
        agent_name=execution.agent_name,
        status=execution.status,
        request_id=request_id,
        query=_optional_string(input_data.get("user_query")),
        route=_optional_string(output_data.get("route")),
        route_reason=_optional_string(output_data.get("route_reason")),
        hop_count=_optional_int(output_data.get("hop_count")),
        source_count=_source_count(output_data),
        error=execution.error,
        created_at=execution.created_at,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        duration_ms=_duration_ms(
            execution.started_at,
            execution.completed_at,
        ),
    )


@router.get(
    "",
    response_model=ExecutionListResponse,
)
async def list_executions(
    database: Annotated[
        AsyncDatabase[MongoDocument],
        Depends(get_mongodb_database),
    ],
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
        ),
    ] = 50,
    offset: Annotated[
        int,
        Query(ge=0),
    ] = 0,
) -> ExecutionListResponse:
    repository = AgentExecutionRepository(database)

    try:
        total = await repository.count()

        executions = await repository.list_all(
            limit=limit,
            offset=offset,
        )

    except RepositoryError as exc:
        raise HTTPException(
            status_code=(status.HTTP_503_SERVICE_UNAVAILABLE),
            detail=("Unable to read execution history."),
        ) from exc

    items = [_execution_summary(execution) for execution in executions]

    return ExecutionListResponse(
        total=total,
        count=len(items),
        limit=limit,
        offset=offset,
        executions=items,
    )


@router.get(
    "/{execution_id}",
    response_model=ExecutionDetailResponse,
)
async def get_execution(
    execution_id: str,
    database: Annotated[
        AsyncDatabase[MongoDocument],
        Depends(get_mongodb_database),
    ],
) -> ExecutionDetailResponse:
    execution_repository = AgentExecutionRepository(database)

    workflow_repository = WorkflowHistoryRepository(database)

    try:
        execution = await execution_repository.get(execution_id)

        if execution is None:
            raise HTTPException(
                status_code=(status.HTTP_404_NOT_FOUND),
                detail=("Execution was not found."),
            )

        events = await workflow_repository.list_for_execution(
            execution_id,
            limit=100,
        )

    except HTTPException:
        raise

    except RepositoryError as exc:
        raise HTTPException(
            status_code=(status.HTTP_503_SERVICE_UNAVAILABLE),
            detail=("Unable to read execution details."),
        ) from exc

    return ExecutionDetailResponse(
        execution=_execution_summary(execution),
        input=dict(execution.input),
        output=dict(execution.output),
        events=[
            WorkflowEventResponse(
                id=event.id,
                sequence=event.sequence,
                event_type=event.event_type,
                agent_name=event.agent_name,
                payload=dict(event.payload),
                created_at=event.created_at,
            )
            for event in events
        ],
    )
