from typing import Annotated

from pydantic import BaseModel, StringConstraints

PromptText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=20_000,
    ),
]


class ChatRequest(BaseModel):
    prompt: PromptText


class TokenUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class ChatResponse(BaseModel):
    content: str
    model: str
    usage: TokenUsage