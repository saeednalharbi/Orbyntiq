from dataclasses import dataclass
from typing import Literal

LLMRole = Literal["system", "user", "assistant"]


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: LLMRole
    content: str


@dataclass(frozen=True, slots=True)
class LLMResponse:
    content: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_duration_ns: int | None = None