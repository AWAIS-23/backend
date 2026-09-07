"""
app/ai
------
AI foundation layer for Rising Skills (Phase 6A).

This package provides the provider-agnostic AI infrastructure:
- AIProvider interface (app/ai/provider.py)
- Provider-neutral schemas (app/ai/schemas.py)
- Typed AI exceptions (app/ai/exceptions.py)
- Operational logging helpers (app/ai/logging.py)
- Prompt construction foundation (app/ai/prompts/base.py)
- AIService orchestration layer (app/ai/service.py)

The Groq SDK is deliberately imported ONLY inside app/ai/groq_client.py so
that the rest of the application never depends on a specific AI vendor.
Import the concrete provider explicitly when wiring dependencies:

    from app.ai.groq_client import GroqProvider

ARCHITECTURAL RULE: The deterministic backend remains the source of truth
for all security- and business-critical decisions. This layer is strictly
assistive and must never mutate verified state, scores, or match results.
"""
from app.ai.exceptions import (
    AIInvalidResponseError,
    AIProviderError,
    AIProviderUnavailableError,
    AIRateLimitError,
    AITimeoutError,
)
from app.ai.prompts.base import PromptBuilder
from app.ai.provider import AIProvider
from app.ai.schemas import AIResponse, AIMessage, ResponseFormat
from app.ai.service import AIService

__all__ = [
    "AIInvalidResponseError",
    "AIProvider",
    "AIProviderError",
    "AIProviderUnavailableError",
    "AIResponse",
    "AIRateLimitError",
    "AIService",
    "AIMessage",
    "AITimeoutError",
    "PromptBuilder",
    "ResponseFormat",
]
