from contextvars import ContextVar, Token

_request_id: ContextVar[str | None] = ContextVar(
    "orbyntiq_request_id",
    default=None,
)


def get_request_id() -> str | None:
    """Return the request ID associated with the current context."""
    return _request_id.get()


def set_request_id(request_id: str) -> Token[str | None]:
    """Associate a request ID with the current context."""
    return _request_id.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    """Restore the request context to its previous request ID."""
    _request_id.reset(token)
