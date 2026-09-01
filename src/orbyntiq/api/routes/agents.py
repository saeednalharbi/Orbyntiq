from typing import Annotated

from fastapi import APIRouter, Depends

from orbyntiq.api.dependencies import get_multi_agent_service
from orbyntiq.api.schemas.agents import (
    AgentExecuteRequest,
    AgentExecuteResponse,
)
from orbyntiq.services import MultiAgentService

router = APIRouter(
    prefix="/api/v1/agents",
    tags=["agents"],
)


@router.post(
    "/execute",
    response_model=AgentExecuteResponse,
)
async def execute_agent_request(
    request: AgentExecuteRequest,
    service: Annotated[
        MultiAgentService,
        Depends(get_multi_agent_service),
    ],
) -> AgentExecuteResponse:
    execution = await service.execute(
        request.query,
        request_id=request.request_id,
        max_hops=request.max_hops,
    )

    return AgentExecuteResponse(
        execution_id=execution.execution_id,
        request_id=execution.request_id,
        route=execution.route,
        route_reason=execution.route_reason,
        final_response=execution.final_response,
        sources=[
            dict(source)
            for source in execution.sources
        ],
        errors=list(execution.errors),
        hop_count=execution.hop_count,
    )
