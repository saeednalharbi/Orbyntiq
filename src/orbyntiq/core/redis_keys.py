from dataclasses import dataclass


def _validate_component(value: str, name: str) -> str:
    value = value.strip()

    if not value:
        raise ValueError(f"{name} cannot be empty")

    if ":" in value:
        raise ValueError(f"{name} cannot contain ':'")

    return value


@dataclass(frozen=True, slots=True)
class RedisKeyBuilder:
    environment: str
    prefix: str = "orbyntiq"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "prefix",
            _validate_component(self.prefix, "prefix"),
        )
        object.__setattr__(
            self,
            "environment",
            _validate_component(self.environment, "environment"),
        )

    @property
    def base(self) -> str:
        return f"{self.prefix}:{self.environment}"

    def session(self, session_id: str) -> str:
        session_id = _validate_component(session_id, "session_id")
        return f"{self.base}:session:{session_id}"

    def conversation(self, conversation_id: str) -> str:
        conversation_id = _validate_component(
            conversation_id,
            "conversation_id",
        )
        return f"{self.base}:conversation:{conversation_id}"

    def agent(self, agent_name: str, session_id: str) -> str:
        agent_name = _validate_component(agent_name, "agent_name")
        session_id = _validate_component(session_id, "session_id")

        return f"{self.base}:agent:{agent_name}:{session_id}"

    def cache(self, namespace: str, identifier: str) -> str:
        namespace = _validate_component(namespace, "namespace")
        identifier = _validate_component(identifier, "identifier")

        return f"{self.base}:cache:{namespace}:{identifier}"
