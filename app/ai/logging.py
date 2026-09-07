"""
app/ai/logging.py
-----------------
Operational logging helpers for the AI foundation layer.

Integrates with the project's existing structured logging system
(app/core/logging.py) using the standard ``rising_skills.*`` logger
namespace.

SECURITY: Only operational metadata (feature, model, latency, token usage,
status, error category) is ever logged. The following must NEVER appear in
AI logs:
- API keys or any credential material
- JWTs or Authorization headers
- Raw prompts containing user PII
- Raw model responses
"""
import logging

logger = logging.getLogger("rising_skills.ai")


def log_ai_success(feature: str, response) -> None:
    """Log a successful AI call with operational metadata only."""
    logger.info(
        f"AI call succeeded [feature={feature}] model={response.model} "
        f"latency_ms={response.latency_ms:.1f} "
        f"prompt_tokens={response.prompt_tokens} "
        f"completion_tokens={response.completion_tokens} "
        f"total_tokens={response.total_tokens}"
    )


def log_ai_failure(feature: str, error: Exception) -> None:
    """Log a failed AI call with an error category only (never raw payloads)."""
    error_code = getattr(error, "error_code", None)
    category = error_code.value if hasattr(error_code, "value") else type(error).__name__
    logger.warning(f"AI call failed [feature={feature}] error={category}")


def log_ai_retry(reason: str, attempt: int) -> None:
    """Log a transient provider failure that will be retried."""
    logger.warning(f"AI provider retry [attempt={attempt}] reason={reason}")
