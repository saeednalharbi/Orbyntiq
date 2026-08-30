from collections.abc import Sequence

from orbyntiq.llm.models import LLMMessage


def build_messages(
    user_prompt: str,
    *,
    system_prompt: str | None = None,
    history: Sequence[LLMMessage] = (),
) -> tuple[LLMMessage, ...]:
    """Build a validated conversation for an LLM provider."""

    user_prompt = user_prompt.strip()

    if not user_prompt:
        raise ValueError("User prompt cannot be empty.")

    messages: list[LLMMessage] = []

    if system_prompt:
        system_prompt = system_prompt.strip()

        if system_prompt:
            messages.append(
                LLMMessage(
                    role="system",
                    content=system_prompt,
                )
            )

    messages.extend(history)

    messages.append(
        LLMMessage(
            role="user",
            content=user_prompt,
        )
    )

    return tuple(messages)