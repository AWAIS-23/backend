"""
app/ai/provider.py
------------------
Provider-agnostic AI generation interface.

The AIProvider protocol is the ONLY contract application code depends on.
Concrete implementations (e.g. GroqProvider) translate these neutral calls
into their SDK-specific format and must return AIResponse instances.
Future providers (OpenAI, Anthropic, self-hosted models) can be introduced
without changing the AI service layer or any business logic.
"""
from typing import Protocol, runtime_checkable, Sequence

from app.ai.schemas import AIResponse, AIMessage, ResponseFormat


@runtime_checkable
class AIProvider(Protocol):
    """
    Structural contract every AI provider implementation must satisfy.

    Implementations MUST:
    - Accept provider-neutral AIMessage sequences.
    - Return provider-independent AIResponse instances.
    - Raise typed exceptions from app/ai/exceptions.py on failure.
    - Never leak provider SDK objects through this interface.
    """

    async def generate(
        self,
        messages: Sequence[AIMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: ResponseFormat | None = None,
    ) -> AIResponse:
        """
        Execute a single chat-completion style generation.

        Args:
            messages: Ordered, provider-neutral message list.
            temperature: Optional sampling temperature override.
            max_tokens: Optional completion token budget override.
            response_format: Optional structured output mode. When JSON is
                requested, providers should instruct the model to emit a
                single valid JSON document.
        """
        ...
