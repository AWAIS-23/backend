"""
app/ai/groq_client.py
---------------------
Concrete Groq implementation of the AIProvider interface.

ISOLATION & SECURITY RULES:
1. The Groq SDK is imported and used ONLY inside this module. No route,
   repository, or business service may import Groq directly.
2. Groq SDK objects never escape this module; completions are converted
   into the provider-independent AIResponse schema.
3. The API key is read once from the existing Settings system and is
   never logged or included in exception details.
4. Configuration is NOT duplicated here — all values come from the
   existing GROQ_* settings (app/core/config.py).
5. Safe retry behavior: transient failures (rate limiting, 5xx) are
   retried at most DEFAULT_MAX_RETRIES times with exponential backoff.
   Timeouts, connection errors, and 4xx client errors are never retried.
"""
import asyncio
import time
from typing import Any, Sequence

from groq import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncGroq,
    InternalServerError,
    RateLimitError,
)

from app.ai.exceptions import (
    AIProviderError,
    AIProviderUnavailableError,
    AIRateLimitError,
    AITimeoutError,
)
from app.ai.logging import log_ai_retry
from app.ai.schemas import AIResponse, AIMessage, ResponseFormat
from app.core.config import Settings, get_settings

# Maximum retries (beyond the initial attempt) for transient failures only.
DEFAULT_MAX_RETRIES = 2
# Base delay for exponential backoff between retries (0.5s, 1.0s, ...).
RETRY_BASE_DELAY_SECONDS = 0.5


class GroqProvider:
    """
    Async Groq implementation of the AIProvider interface.

    Wraps ``groq.AsyncGroq`` and manages timeouts, safe retries, and
    exception translation into the project's typed AI exceptions. The SDK's
    own retry mechanism is disabled (max_retries=0) so retry behavior is
    fully controlled and observable here.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_base_delay: float = RETRY_BASE_DELAY_SECONDS,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative.")
        if retry_base_delay < 0:
            raise ValueError("retry_base_delay must be non-negative.")

        self._settings = settings if settings is not None else get_settings()
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay

        api_key = self._settings.GROQ_API_KEY
        if not api_key:
            raise AIProviderUnavailableError(
                "AI provider is not configured: GROQ_API_KEY is missing."
            )

        self._client = AsyncGroq(
            api_key=api_key,
            timeout=self._settings.GROQ_TIMEOUT_SECONDS,
            max_retries=0,  # retries are managed here, not by the SDK
        )

    @property
    def model(self) -> str:
        """The configured Groq model identifier."""
        return self._settings.GROQ_MODEL

    async def generate(
        self,
        messages: Sequence[AIMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: ResponseFormat | None = None,
    ) -> AIResponse:
        """Execute a chat completion against the Groq API."""
        request_kwargs: dict[str, Any] = {
            "model": self._settings.GROQ_MODEL,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": (
                self._settings.GROQ_TEMPERATURE if temperature is None else temperature
            ),
            "max_tokens": (
                self._settings.GROQ_MAX_TOKENS if max_tokens is None else max_tokens
            ),
        }
        if response_format is not None:
            # Groq expects the OpenAI-style response format mapping. When JSON
            # mode is used, the prompt itself must mention "json" (feature
            # prompts in later phases must honour this requirement).
            request_kwargs["response_format"] = {"type": response_format.value}

        started = time.perf_counter()
        attempt = 0

        while True:
            try:
                completion = await self._client.chat.completions.create(**request_kwargs)
            except APITimeoutError as exc:
                raise AITimeoutError(
                    f"The AI provider did not respond within "
                    f"{self._settings.GROQ_TIMEOUT_SECONDS} seconds."
                ) from exc
            except RateLimitError as exc:
                if attempt < self._max_retries:
                    attempt += 1
                    log_ai_retry("rate_limited", attempt)
                    await asyncio.sleep(self._retry_base_delay * (2 ** (attempt - 1)))
                    continue
                raise AIRateLimitError(details={"provider": "groq"}) from exc
            except InternalServerError as exc:
                if attempt < self._max_retries:
                    attempt += 1
                    log_ai_retry("server_error", attempt)
                    await asyncio.sleep(self._retry_base_delay * (2 ** (attempt - 1)))
                    continue
                raise AIProviderError(
                    "The AI provider returned a persistent server error.",
                    details={"provider": "groq"},
                ) from exc
            except APIConnectionError as exc:
                # Non-timeout connection failures are not retried here.
                raise AIProviderUnavailableError(
                    "Could not connect to the AI provider."
                ) from exc
            except APIStatusError as exc:
                # Other 4xx client errors (authentication, bad request, ...)
                # are never retried. Only the status code is surfaced in
                # details — never the raw response body.
                raise AIProviderError(
                    "The AI provider rejected the request.",
                    details={"provider": "groq", "status_code": exc.status_code},
                ) from exc
            except Exception as exc:
                # Defensive boundary: any unexpected SDK/runtime failure is
                # wrapped so no SDK exception type escapes this module.
                raise AIProviderError(
                    "An unexpected AI provider failure occurred."
                ) from exc

            latency_ms = (time.perf_counter() - started) * 1000.0
            return self._to_ai_response(completion, latency_ms)

    def _to_ai_response(self, completion: Any, latency_ms: float) -> AIResponse:
        """Convert a Groq SDK completion into the neutral AIResponse schema."""
        content = ""
        choices = getattr(completion, "choices", None) or []
        if choices:
            message = getattr(choices[0], "message", None)
            content = (getattr(message, "content", None) or "") if message else ""

        usage = getattr(completion, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", None) or 0
        completion_tokens = getattr(usage, "completion_tokens", None) or 0
        total_tokens = getattr(usage, "total_tokens", None) or (
            prompt_tokens + completion_tokens
        )
        model = getattr(completion, "model", None) or self._settings.GROQ_MODEL

        return AIResponse(
            content=content,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
        )
