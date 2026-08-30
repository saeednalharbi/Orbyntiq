class LLMProviderError(Exception):
    """Base exception for LLM provider failures."""


class LLMTimeoutError(LLMProviderError):
    """Raised when an LLM provider exceeds its configured timeout."""


class LLMConnectionError(LLMProviderError):
    """Raised when Orbyntiq cannot connect to an LLM provider."""


class LLMModelNotFoundError(LLMProviderError):
    """Raised when the configured model is unavailable."""


class LLMHTTPError(LLMProviderError):
    """Raised when the provider returns an unexpected HTTP error."""


class LLMInvalidResponseError(LLMProviderError):
    """Raised when the provider returns malformed or invalid data."""