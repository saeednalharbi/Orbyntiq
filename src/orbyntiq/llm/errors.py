class LLMProviderError(Exception):
    """Base exception for LLM provider failures."""


class LLMTimeoutError(LLMProviderError):
    """Raised when an LLM provider exceeds its configured timeout."""


class LLMConnectionError(LLMProviderError):
    """Raised when Orbyntiq cannot connect to an LLM provider."""