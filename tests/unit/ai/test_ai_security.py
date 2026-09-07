"""
Security-focused unit tests for the AI foundation.

Verifies the architectural isolation guarantees:
1. The Groq SDK is imported only inside the provider implementation.
2. API keys never appear in logs or exception payloads.
3. Authorization/JWT material is never passed to providers by the service.
4. Provider SDK objects never escape the provider layer.
5. Untrusted user content is always delimited (defense against prompt injection).
"""
import logging
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from groq import RateLimitError

from app.ai.exceptions import AIProviderError, AIRateLimitError
from app.ai.groq_client import GroqProvider
from app.ai.prompts.base import PromptBuilder
from app.ai.schemas import AIResponse, AIMessage
from app.ai.service import AIService
from app.core.config import Settings

TEST_API_KEY = "test-groq-api-key-do-not-log"
BACKEND_ROOT = Path(__file__).resolve().parents[3]
PROVIDER_MODULE = BACKEND_ROOT / "app" / "ai" / "groq_client.py"


@pytest.fixture
def groq_settings() -> Settings:
    return Settings(
        APP_ENV="testing",
        SUPABASE_JWT_SECRET="test-jwt-secret-1234567890-test-secret-32bytes",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        GROQ_API_KEY=TEST_API_KEY,
    )


class FakeProvider:
    def __init__(self):
        self.calls: list[dict] = []

    async def generate(self, messages, *, temperature=None, max_tokens=None, response_format=None):
        self.calls.append({"messages": list(messages)})
        return AIResponse(content="{}", model="fake-model")


class TestGroqSdkIsolation:
    def test_groq_sdk_imported_only_in_provider_module(self):
        """Architectural guard: no production module outside groq_client.py
        may import the Groq SDK."""
        app_dir = BACKEND_ROOT / "app"
        offenders: list[str] = []
        for py_file in app_dir.rglob("*.py"):
            if py_file == PROVIDER_MODULE:
                continue
            source = py_file.read_text(encoding="utf-8")
            for line in source.splitlines():
                stripped = line.strip()
                if (
                    stripped.startswith("import groq")
                    or stripped.startswith("from groq")
                ):
                    offenders.append(f"{py_file.relative_to(BACKEND_ROOT)}: {stripped}")
        assert offenders == []

    def test_provider_layer_returns_no_sdk_objects(self, groq_settings: Settings):
        from types import SimpleNamespace

        completion = SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content="hello"))
            ],
            model="llama-3.3-70b-versatile",
            usage=SimpleNamespace(
                prompt_tokens=1, completion_tokens=2, total_tokens=3
            ),
        )
        with patch("app.ai.groq_client.AsyncGroq") as mock_groq_class:
            mock_client = mock_groq_class.return_value
            mock_client.chat.completions.create = AsyncMock(return_value=completion)
            provider = GroqProvider(groq_settings)

            result = provider._to_ai_response(completion, 1.0)

        assert isinstance(result, AIResponse)
        assert not isinstance(result, SimpleNamespace)


class TestCredentialProtection:
    async def test_api_key_never_logged_on_failure(
        self, groq_settings: Settings, caplog
    ):
        request = httpx.Request("POST", "https://api.groq.com/x")
        rate_error = RateLimitError(
            "rl", response=httpx.Response(429, request=request), body=None
        )
        with patch("app.ai.groq_client.AsyncGroq") as mock_groq_class:
            mock_client = mock_groq_class.return_value
            mock_client.chat.completions.create = AsyncMock(side_effect=rate_error)
            provider = GroqProvider(groq_settings, max_retries=0)

            with caplog.at_level(logging.DEBUG):
                with pytest.raises(AIRateLimitError):
                    await provider.generate([AIMessage(role="user", content="hi")])

        assert TEST_API_KEY not in caplog.text

    async def test_api_key_not_in_exception_string(self, groq_settings: Settings):
        request = httpx.Request("POST", "https://api.groq.com/x")
        rate_error = RateLimitError(
            "rl", response=httpx.Response(429, request=request), body=None
        )
        with patch("app.ai.groq_client.AsyncGroq") as mock_groq_class:
            mock_client = mock_groq_class.return_value
            mock_client.chat.completions.create = AsyncMock(side_effect=rate_error)
            provider = GroqProvider(groq_settings, max_retries=0)

            with pytest.raises(AIProviderError) as exc_info:
                await provider.generate([AIMessage(role="user", content="hi")])

        assert TEST_API_KEY not in str(exc_info.value)
        assert TEST_API_KEY not in repr(exc_info.value)


class TestAuthorizationBoundary:
    async def test_service_never_passes_auth_material_to_provider(self):
        """AIService has no access to request context; verify a normal call
        contains no Authorization headers, Bearer tokens, or JWTs."""
        provider = FakeProvider()
        service = AIService(provider)
        prompt = (
            PromptBuilder(system="You are a coach.")
            .add_context("match", {"overall_score": 50.0})
            .add_user_input("note", "plain user text")
        )

        await service.complete(prompt, feature="security-test")

        messages = provider.calls[0]["messages"]
        for message in messages:
            assert "Authorization" not in message.content
            assert "Bearer " not in message.content
            assert "eyJ" not in message.content

    async def test_jwt_user_input_only_inside_untrusted_delimiters(self):
        """When a JWT appears in user input, it is delivered strictly as
        delimited data — never as a system-level instruction."""
        provider = FakeProvider()
        service = AIService(provider)
        fake_jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.sig"
        prompt = (
            PromptBuilder(system="You are a coach.")
            .add_user_input("pasted_token", f"Bearer {fake_jwt}")
        )

        await service.complete(prompt, feature="security-test")

        messages = provider.calls[0]["messages"]
        system = messages[0].content
        user = messages[1].content

        assert fake_jwt not in system
        start = user.index("<untrusted_data>") + len("<untrusted_data>")
        end = user.index("</untrusted_data>")
        assert fake_jwt in user[start:end]
