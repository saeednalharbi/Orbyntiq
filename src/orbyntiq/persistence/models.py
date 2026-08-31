from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")

    utc_value = value.astimezone(UTC)

    return utc_value.replace(
        microsecond=(
            utc_value.microsecond // 1000
        )
        * 1000
    )


def normalize_optional_datetime(
    value: datetime | None,
) -> datetime | None:
    if value is None:
        return None

    return normalize_datetime(value)


def utc_now() -> datetime:
    return normalize_datetime(
        datetime.now(UTC)
    )


def new_entity_id() -> str:
    return str(uuid4())


class User(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        validate_default=True,
    )

    id: str = Field(
        default_factory=new_entity_id,
        min_length=1,
    )
    email: str = Field(
        min_length=3,
        max_length=254,
    )
    display_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    status: Literal[
        "active",
        "disabled",
    ] = "active"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip().lower()

        if (
            "@" not in normalized
            or normalized.startswith("@")
            or normalized.endswith("@")
        ):
            raise ValueError("email must be valid")

        return normalized

    @field_validator(
        "created_at",
        "updated_at",
        mode="after",
    )
    @classmethod
    def normalize_timestamps(
        cls,
        value: datetime,
    ) -> datetime:
        return normalize_datetime(value)


class Conversation(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        validate_default=True,
    )

    id: str = Field(
        default_factory=new_entity_id,
        min_length=1,
    )
    user_id: str = Field(min_length=1)
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    status: Literal["active", "archived"] = "active"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator(
        "created_at",
        "updated_at",
        mode="after",
    )
    @classmethod
    def normalize_timestamps(
        cls,
        value: datetime,
    ) -> datetime:
        return normalize_datetime(value)


class Message(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        validate_default=True,
    )

    id: str = Field(
        default_factory=new_entity_id,
        min_length=1,
    )
    conversation_id: str = Field(min_length=1)
    role: Literal[
        "system",
        "user",
        "assistant",
        "tool",
    ]
    content: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator(
        "created_at",
        mode="after",
    )
    @classmethod
    def normalize_timestamp(
        cls,
        value: datetime,
    ) -> datetime:
        return normalize_datetime(value)


class AgentExecution(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        validate_default=True,
    )

    id: str = Field(
        default_factory=new_entity_id,
        min_length=1,
    )
    conversation_id: str = Field(min_length=1)
    agent_name: str = Field(
        min_length=1,
        max_length=100,
    )
    status: Literal[
        "queued",
        "running",
        "completed",
        "failed",
    ] = "queued"
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = Field(
        default=None,
        min_length=1,
    )
    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @field_validator(
        "created_at",
        mode="after",
    )
    @classmethod
    def normalize_created_at(
        cls,
        value: datetime,
    ) -> datetime:
        return normalize_datetime(value)

    @field_validator(
        "started_at",
        "completed_at",
        mode="after",
    )
    @classmethod
    def normalize_optional_timestamps(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        return normalize_optional_datetime(value)


class WorkflowHistory(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        validate_default=True,
    )

    id: str = Field(
        default_factory=new_entity_id,
        min_length=1,
    )
    execution_id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    sequence: int = Field(ge=0)
    event_type: str = Field(
        min_length=1,
        max_length=100,
    )
    agent_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator(
        "created_at",
        mode="after",
    )
    @classmethod
    def normalize_timestamp(
        cls,
        value: datetime,
    ) -> datetime:
        return normalize_datetime(value)