from typing import Annotated

from fastapi import APIRouter, Depends

from orbyntiq.api.dependencies import get_llm_service
from orbyntiq.api.schemas.llm import ChatRequest, ChatResponse, TokenUsage
from orbyntiq.services import LLMService

router = APIRouter(
    prefix="/api/v1/llm",
    tags=["llm"],
)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: Annotated[LLMService, Depends(get_llm_service)],
) -> ChatResponse:
    response = await service.chat(request.prompt)

    return ChatResponse(
        content=response.content,
        model=response.model,
        usage=TokenUsage(
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
        ),
    )