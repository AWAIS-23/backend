"""
Unit tests for GroqProvider. No real Groq API calls are ever made — the
AsyncGroq SDK client is fully mocked.

Covers: configuration wiring, successful response conversion, exception
translation, safe retry behavior, response-format mapping, and API key
confidentiality.
"""
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from groq import (
    APIConnectionError,
    AuthenticationError,
    InternalServerError,
    RateLimitError,
)

from app.ai.exceptions import (
    AIProviderError,
    AIProviderUnavailableError,
    AIRateLimitError,
    AITimeoutError,
)
from app.ai.groq_client import GroqProvider
from app.ai.schemas import AIResponse, AIMessage, ResponseFormat
from app.core.config import Settings
from app.core.exceptions import AppException

TEST_API_KEY = "test-groq-api-key-do-not-log"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


@pytest.fixture
def groq_settings() -> Settings:
    return Settings(
        APP_ENV="testing",
        SUPABASE_JWT_SECRET="test-jwt-secret-1234567890-test-secret-32bytes",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        GROQ_API_KEY=TEST_API_KEY,
    )


def make_messages() -> list[AIMessage]:
    return [
        AIMessage(role="system", content="You are a tester."),
        AIMessage(role="user", content="Say hello."),
    ]


def make_completion(
    content: str = "Hello!",
    model: str = "llama-3.3-70b-versatile",
    prompt_tokens: int = 25,
    completion_tokens: int = 40,
) -> SimpleNamespace:
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        model=model,
        usage=usage,
    )


def make_request() -> httpx.Request:
    return httpx.Request("POST", GROQ_URL)


def rate_limit_error() -> RateLimitError:
    return RateLimitError(
        "rate limited", response=httpx.Response(429, request=make_request()), body=None
    )


def server_error() -> InternalServerError:
    return InternalServerError(
        "server error", response=httpx.Response(500, request=make_request()), body=None
    )


def auth_error() -> AuthenticationError:
    return AuthenticationError(
        "invalid key", response=httpx.Response(401, request=make_request()), body=None
    )


@pytest.fixture
def patched_groq():
    """Patch the AsyncGroq SDK class inside the provider module."""
    with patch("app.ai.groq_client.AsyncGroq") as mock_groq_class:
        mock_client = mock_groq_class.return_value
        mock_client.chat.completions.create = AsyncMock(return_value=make_completion())
        yield mock_client


class TestConstruction:
    def test_missing_api_key_raises_unavailable(self, groq_settings: Settings):
        settings_no_key = groq_settings.model_copy(update={"GROQ_API_KEY": None})
        with pytest.raises(AIProviderUnavailableError):
            GroqProvider(settings_no_key)

    def test_missing_api_key_via_default_settings(self):
        with patch("app.ai.groq_client.get_settings") as mock_settings:
            mock_settings.return_value = Settings(
                APP_ENV="testing",
                SUPABASE_JWT_SECRET="test-secret",
                DATABASE_URL="sqlite+aiosqlite:///:memory:",
                GROQ_API_KEY=None,
            )
            with pytest.raises(AIProviderUnavailableError):
                GroqProvider()

    def test_negative_retries_rejected(self, groq_settings: Settings):
        with pytest.raises(ValueError):
            GroqProvider(groq_settings, max_retries=-1)


class TestSuccessfulGeneration:
    async def test_successful_response_converts_to_ai_response(
        self, groq_settings: Settings, patched_groq
    ):
        provider = GroqProvider(groq_settings)
        result = await provider.generate(make_messages())

        assert isinstance(result, AIResponse)
        assert result.content == "Hello!"
        assert result.model == "llama-3.3-70b-versatile"
        assert result.prompt_tokens == 25
        assert result.completion_tokens == 40
        assert result.total_tokens == 65
        assert result.latency_ms >= 0.0

    async def test_defaults_from_settings_used(
        self, groq_settings: Settings, patched_groq
    ):
        provider = GroqProvider(groq_settings)
        await provider.generate(make_messages())

        kwargs = patched_groq.chat.completions.create.call_args.kwargs
        assert kwargs["model"] == "llama-3.3-70b-versatile"
        assert kwargs["temperature"] == 0.2
        assert kwargs["max_tokens"] == 2048
        assert "response_format" not in kwargs
        assert kwargs["messages"] == [
            {"role": "system", "content": "You are a tester."},
            {"role": "user", "content": "Say hello."},
        ]

    async def test_overrides_applied(self, groq_settings: Settings, patched_groq):
        provider = GroqProvider(groq_settings)
        await provider.generate(
            make_messages(), temperature=0.9, max_tokens=512
        )

        kwargs = patched_groq.chat.completions.create.call_args.kwargs
        assert kwargs["temperature"] == 0.9
        assert kwargs["max_tokens"] == 512

    async def test_json_response_format_mapped(
        self, groq_settings: Settings, patched_groq
    ):
        provider = GroqProvider(groq_settings)
        await provider.generate(make_messages(), response_format=ResponseFormat.JSON)

        kwargs = patched_groq.chat.completions.create.call_args.kwargs
        assert kwargs["response_format"] == {"type": "json_object"}

    async def test_text_response_format_mapped(
        self, groq_settings: Settings, patched_groq
    ):
        provider = GroqProvider(groq_settings)
        await provider.generate(make_messages(), response_format=ResponseFormat.TEXT)

        kwargs = patched_groq.chat.completions.create.call_args.kwargs
        assert kwargs["response_format"] == {"type": "text"}

    async def test_empty_content_handled(self, groq_settings: Settings, patched_groq):
        patched_groq.chat.completions.create = AsyncMock(
            return_value=make_completion(content="")
        )
        provider = GroqProvider(groq_settings)
        result = await provider.generate(make_messages())
        assert result.content == ""

    async def test_sdk_objects_do_not_escape(self, groq_settings: Settings, patched_groq):
        provider = GroqProvider(groq_settings)
        result = await provider.generate(make_messages())

        assert isinstance(result, AIResponse)
        assert not isinstance(result, SimpleNamespace)


class TestExceptionTranslation:
    async def test_timeout_maps_to_ai_timeout(
        self, groq_settings: Settings, patched_groq
    ):
        import groq

        patched_groq.chat.completions.create = AsyncMock(
            side_effect=groq.APITimeoutError(request=make_request())
        )
        provider = GroqProvider(groq_settings)

        with pytest.raises(AITimeoutError) as exc_info:
            await provider.generate(make_messages())
        assert exc_info.value.__cause__ is not None
        patched_groq.chat.completions.create.assert_awaited_once()

    async def test_rate_limit_no_retries_raises(
        self, groq_settings: Settings, patched_groq
    ):
        patched_groq.chat.completions.create = AsyncMock(side_effect=rate_limit_error())
        provider = GroqProvider(groq_settings, max_retries=0)

        with pytest.raises(AIRateLimitError):
            await provider.generate(make_messages())
        patched_groq.chat.completions.create.assert_awaited_once()

    async def test_rate_limit_retries_then_raises(
        self, groq_settings: Settings, patched_groq
    ):
        patched_groq.chat.completions.create = AsyncMock(side_effect=rate_limit_error())
        provider = GroqProvider(groq_settings, max_retries=2, retry_base_delay=0.0)

        with pytest.raises(AIRateLimitError):
            await provider.generate(make_messages())
        # Initial attempt + 2 retries = 3 calls.
        assert patched_groq.chat.completions.create.await_count == 3

    async def test_rate_limit_recovers_after_retry(
        self, groq_settings: Settings, patched_groq
    ):
        completion = make_completion()
        patched_groq.chat.completions.create = AsyncMock(
            side_effect=[rate_limit_error(), rate_limit_error(), completion]
        )
        provider = GroqProvider(groq_settings, max_retries=2, retry_base_delay=0.0)

        result = await provider.generate(make_messages())
        assert isinstance(result, AIResponse)
        assert result.content == "Hello!"
        assert patched_groq.chat.completions.create.await_count == 3

    async def test_server_error_retries_then_raises(
        self, groq_settings: Settings, patched_groq
    ):
        patched_groq.chat.completions.create = AsyncMock(side_effect=server_error())
        provider = GroqProvider(groq_settings, max_retries=2, retry_base_delay=0.0)

        with pytest.raises(AIProviderError) as exc_info:
            await provider.generate(make_messages())
        assert not isinstance(exc_info.value, AIRateLimitError)
        assert patched_groq.chat.completions.create.await_count == 3

    async def test_server_error_recovers_after_retry(
        self, groq_settings: Settings, patched_groq
    ):
        completion = make_completion()
        patched_groq.chat.completions.create = AsyncMock(
            side_effect=[server_error(), completion]
        )
        provider = GroqProvider(groq_settings, max_retries=2, retry_base_delay=0.0)

        result = await provider.generate(make_messages())
        assert result.content == "Hello!"
        assert patched_groq.chat.completions.create.await_count == 2

    async def test_connection_error_not_retried(
        self, groq_settings: Settings, patched_groq
    ):
        patched_groq.chat.completions.create = AsyncMock(
            side_effect=APIConnectionError(message="conn", request=make_request())
        )
        provider = GroqProvider(groq_settings, max_retries=2, retry_base_delay=0.0)

        with pytest.raises(AIProviderUnavailableError):
            await provider.generate(make_messages())
        patched_groq.chat.completions.create.assert_awaited_once()

    async def test_client_error_not_retried(
        self, groq_settings: Settings, patched_groq
    ):
        patched_groq.chat.completions.create = AsyncMock(side_effect=auth_error())
        provider = GroqProvider(groq_settings, max_retries=2, retry_base_delay=0.0)

        with pytest.raises(AIProviderError) as exc_info:
            await provider.generate(make_messages())

        assert not isinstance(exc_info.value, AIRateLimitError)
        assert not isinstance(exc_info.value, AITimeoutError)
        assert exc_info.value.details.get("status_code") == 401
        patched_groq.chat.completions.create.assert_awaited_once()

    async def test_unexpected_error_wrapped(
        self, groq_settings: Settings, patched_groq
    ):
        patched_groq.chat.completions.create = AsyncMock(
            side_effect=RuntimeError("unexpected")
        )
        provider = GroqProvider(groq_settings)

        with pytest.raises(AIProviderError):
            await provider.generate(make_messages())

    async def test_ai_exceptions_integrate_with_app_exception_convention(
        self, groq_settings: Settings, patched_groq
    ):
        patched_groq.chat.completions.create = AsyncMock(
            side_effect=APIConnectionError(message="conn", request=make_request())
        )
        provider = GroqProvider(groq_settings)
        from app.core.constants import ErrorCode

        with pytest.raises(AIProviderUnavailableError) as exc_info:
            await provider.generate(make_messages())
        assert isinstance(exc_info.value, AppException)
        assert exc_info.value.error_code == ErrorCode.AI_PROVIDER_ERROR
        assert exc_info.value.status_code == 503


class TestConfidentiality:
    async def test_api_key_never_logged(
        self, groq_settings: Settings, patched_groq, caplog
    ):
        patched_groq.chat.completions.create = AsyncMock(side_effect=rate_limit_error())
        provider = GroqProvider(groq_settings, max_retries=0)

        with caplog.at_level(logging.DEBUG, logger="rising_skills.ai"):
            with pytest.raises(AIRateLimitError):
                await provider.generate(make_messages())

        assert TEST_API_KEY not in caplog.text

    async def test_api_key_not_in_exception_details(
        self, groq_settings: Settings, patched_groq
    ):
        patched_groq.chat.completions.create = AsyncMock(side_effect=auth_error())
        provider = GroqProvider(groq_settings)

        with pytest.raises(AIProviderError) as exc_info:
            await provider.generate(make_messages())

        assert TEST_API_KEY not in str(exc_info.value.details)
        assert TEST_API_KEY not in str(exc_info.value)
