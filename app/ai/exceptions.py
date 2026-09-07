"""
app/ai/exceptions.py
--------------------
Typed AI-layer exceptions integrating with the existing AppException
convention (app/core/exceptions.py), so future routes automatically emit
the project's standard RFC-7807 error envelopes.

DESIGN RULES:
- AI failures must NEVER break deterministic Rising Skills flows. These
  exceptions are raised so future API/service layers can decide appropriate
  fallback behavior (graceful degradation instead of hard failure).
- Original provider error context is preserved internally via exception
  chaining (``raise ... from exc``) and never exposes provider secrets.
- Nothing is silently swallowed; every failure surfaces as a typed error.
"""
from typing import Any

from fastapi import status

from app.core.constants import ErrorCode
from app.core.exceptions import AppException


class AIProviderError(AppException):
    """
    Base class for all AI provider failures.

    Details may carry provider-neutral diagnostics (e.g. HTTP status codes)
    but must never contain API keys, raw prompts, or credentials.
    """
    error_code: ErrorCode = ErrorCode.AI_PROVIDER_ERROR
    http_status: int = status.HTTP_503_SERVICE_UNAVAILABLE
    default_message: str = "The AI provider failed to complete the request."

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            status_code=self.http_status,
            error_code=self.error_code,
            message=message or self.default_message,
            details=details,
        )


class AIProviderUnavailableError(AIProviderError):
    """The provider could not be reached or is not configured (e.g. missing API key)."""
    default_message: str = "The AI provider is currently unavailable or not configured."


class AITimeoutError(AIProviderError):
    """The provider did not respond within the configured timeout."""
    error_code: ErrorCode = ErrorCode.AI_TIMEOUT
    http_status: int = status.HTTP_504_GATEWAY_TIMEOUT
    default_message: str = "The AI provider did not respond within the configured timeout."


class AIRateLimitError(AIProviderError):
    """The provider rate limit was exceeded even after safe retries."""
    error_code: ErrorCode = ErrorCode.AI_RATE_LIMIT
    http_status: int = status.HTTP_429_TOO_MANY_REQUESTS
    default_message: str = "The AI provider rate limit was exceeded. Please try again later."


class AIInvalidResponseError(AIProviderError):
    """The provider returned malformed or schema-invalid content."""
    error_code: ErrorCode = ErrorCode.AI_INVALID_RESPONSE
    http_status: int = status.HTTP_502_BAD_GATEWAY
    default_message: str = "The AI provider returned an invalid response."
