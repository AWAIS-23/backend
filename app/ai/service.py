"""
app/ai/service.py
-----------------
AIService — orchestration layer between future application features and the
AIProvider abstraction.

Foundation responsibilities:
1. Receive structured prompt input (PromptBuilder).
2. Call the provider abstraction (never a concrete SDK).
3. Log operational metadata (feature, model, latency, tokens, outcome).
4. Validate structured output against a caller-provided Pydantic model.

EXPLICITLY OUT OF SCOPE (must remain in deterministic backend services):
- SQL queries / repository implementations
- Authentication or RBAC decisions
- Assessment scoring, skill-gap calculations, or matching
- Evidence verification or any state mutation
The AI layer is strictly assistive and read-only with respect to domain data.
"""
import json
from typing import Any, Type, TypeVar

from pydantic import BaseModel, ValidationError

from app.ai.exceptions import AIInvalidResponseError, AIProviderError
from app.ai.logging import log_ai_failure, log_ai_success
from app.ai.prompts.base import PromptBuilder
from app.ai.schemas import AIResponse, ResponseFormat

T = TypeVar("T", bound=BaseModel)

# Sanity bound for sampling temperature overrides.
MAX_TEMPERATURE = 2.0


class AIService:
    """
    High-level orchestration over an injected AIProvider.

    The service is provider-agnostic: swapping Groq for any other provider
    requires only constructing AIService with a different provider instance.
    """

    def __init__(self, provider: Any) -> None:
        if provider is None:
            raise ValueError("AIService requires an AIProvider instance.")
        self._provider = provider

    async def complete(
        self,
        prompt: PromptBuilder,
        *,
        feature: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AIResponse:
        """
        Execute a free-form (unvalidated) generation.

        Args:
            prompt: Built via PromptBuilder (trusted/untrusted separation).
            feature: Feature identifier used purely for operational logging.
            temperature: Optional provider temperature override.
            max_tokens: Optional token budget override.
        """
        _validate_generation_params(temperature, max_tokens)

        try:
            response = await self._provider.generate(
                prompt.build(),
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except AIProviderError as exc:
            log_ai_failure(feature, exc)
            raise
        except Exception as exc:
            # Defensive boundary: wrap unexpected provider-layer failures so
            # callers only ever see typed AI exceptions.
            error = AIProviderError("An unexpected AI provider failure occurred.")
            log_ai_failure(feature, error)
            raise error from exc

        log_ai_success(feature, response)
        return response

    async def generate_structured(
        self,
        prompt: PromptBuilder,
        *,
        feature: str,
        response_model: Type[T],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> T:
        """
        Execute a generation whose output must validate against a Pydantic model.

        The provider is asked for JSON output via the generic structured-output
        capability, the returned content is parsed, and the payload is validated
        against ``response_model``. Malformed JSON or schema violations raise
        AIInvalidResponseError with the original cause preserved.
        """
        _validate_generation_params(temperature, max_tokens)

        try:
            response = await self._provider.generate(
                prompt.build(),
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=ResponseFormat.JSON,
            )
        except AIProviderError as exc:
            log_ai_failure(feature, exc)
            raise
        except Exception as exc:
            error = AIProviderError("An unexpected AI provider failure occurred.")
            log_ai_failure(feature, error)
            raise error from exc

        log_ai_success(feature, response)

        try:
            payload = _parse_json_payload(response.content)
        except json.JSONDecodeError as exc:
            error = AIInvalidResponseError(
                "The AI provider returned malformed JSON that could not be parsed.",
                details={"feature": feature},
            )
            log_ai_failure(feature, error)
            raise error from exc

        try:
            return response_model.model_validate(payload)
        except ValidationError as exc:
            error = AIInvalidResponseError(
                "The AI provider response did not match the expected schema.",
                details={"feature": feature, "response_model": response_model.__name__},
            )
            log_ai_failure(feature, error)
            raise error from exc


def _validate_generation_params(
    temperature: float | None,
    max_tokens: int | None,
) -> None:
    """Reject invalid generation overrides before contacting any provider."""
    if temperature is not None and not (0.0 <= temperature <= MAX_TEMPERATURE):
        raise ValueError(f"temperature must be between 0.0 and {MAX_TEMPERATURE}.")
    if max_tokens is not None and max_tokens < 1:
        raise ValueError("max_tokens must be a positive integer.")


def _parse_json_payload(content: str) -> Any:
    """
    Parse JSON content, tolerating a single markdown code fence wrapper.

    Models occasionally wrap JSON payloads in ```json fences even when JSON
    mode is requested; stripping one wrapper improves robustness without
    accepting arbitrary non-JSON output.
    """
    text = content.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        stripped = text.rstrip()
        if stripped.endswith("```"):
            text = stripped[:-3]
    return json.loads(text)
