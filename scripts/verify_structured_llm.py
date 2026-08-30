import asyncio
from typing import Literal

from pydantic import BaseModel, Field

from orbyntiq.core.config import get_settings
from orbyntiq.llm import create_llm_provider
from orbyntiq.services import LLMService


class RoutingDecision(BaseModel):
    agent: Literal["research", "planner", "executor"]
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


async def main() -> None:
    settings = get_settings()

    service = LLMService(
        create_llm_provider(settings)
    )

    result = await service.chat_structured(
        (
            "A user asks you to research the latest developments in an AI topic. "
            "Choose the most appropriate agent."
        ),
        RoutingDecision,
    )

    print(result.model_dump())


if __name__ == "__main__":
    asyncio.run(main())