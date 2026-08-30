import pytest

from orbyntiq.llm import LLMMessage, build_messages


def test_build_messages_with_system_prompt():
    messages = build_messages(
        "Hello",
        system_prompt="You are Orbyntiq.",
    )

    assert messages == (
        LLMMessage(role="system", content="You are Orbyntiq."),
        LLMMessage(role="user", content="Hello"),
    )


def test_build_messages_with_history():
    history = (
        LLMMessage(role="user", content="First question"),
        LLMMessage(role="assistant", content="First answer"),
    )

    messages = build_messages(
        "Second question",
        system_prompt="System",
        history=history,
    )

    assert messages[0].role == "system"
    assert messages[1:3] == history
    assert messages[-1] == LLMMessage(
        role="user",
        content="Second question",
    )


def test_build_messages_rejects_empty_prompt():
    with pytest.raises(
        ValueError,
        match="User prompt cannot be empty",
    ):
        build_messages("   ")