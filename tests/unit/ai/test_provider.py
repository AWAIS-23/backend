"""
Unit tests for the AI provider abstraction and neutral schemas.

These tests verify the provider-independent contract: message typing,
response metadata validation, and structural compliance of both a
reference implementation and the concrete GroqProvider.
"""
import pytest
from pydantic import ValidationError

from app.ai.groq_client import GroqProvider
from app.ai.provider import AIProvider
from app.ai.schemas import AIResponse, AIMessage, ResponseFormat
from app.core.config import Settings


class EchoProvider:
    """Minimal reference implementation of the AIProvider interface."""

    def __init__(self, response: AIResponse):
        self._response = response
        self.calls: list[dict] = []

    async def generate(
        self,
        messages,
        *,
        temperature=None,
        max_tokens=None,
        response_format=None,
    ) -> AIResponse:
        self.calls.append(
            {
                "messages": list(messages),
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": response_format,
            }
        )
        return self._response


@pytest.fixture
def sample_response() -> AIResponse:
    return AIResponse(
        content="Analysis complete.",
        model="llama-3.3-70b-versatile",
        prompt_tokens=120,
        completion_tokens=80,
        total_tokens=200,
        latency_ms=543.2,
    )


@pytest.fixture
def groq_settings() -> Settings:
    return Settings(
        APP_ENV="testing",
        SUPABASE_JWT_SECRET="test-jwt-secret-1234567890-test-secret-32bytes",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        GROQ_API_KEY="test-groq-api-key-do-not-log",
    )


class TestAIMessage:
    def test_accepts_valid_roles(self):
        for role in ("system", "user", "assistant"):
            msg = AIMessage(role=role, content="hello")
            assert msg.role == role

    def test_rejects_invalid_role(self):
        with pytest.raises(ValidationError):
            AIMessage(role="tool", content="hello")

    def test_rejects_missing_content(self):
        with pytest.raises(ValidationError):
            AIMessage(role="user")


class TestAIResponse:
    def test_holds_all_metadata(self, sample_response: AIResponse):
        assert sample_response.content == "Analysis complete."
        assert sample_response.model == "llama-3.3-70b-versatile"
        assert sample_response.prompt_tokens == 120
        assert sample_response.completion_tokens == 80
        assert sample_response.total_tokens == 200
        assert sample_response.latency_ms == 543.2

    def test_token_defaults_are_zero(self):
        response = AIResponse(content="hi", model="m")
        assert response.prompt_tokens == 0
        assert response.completion_tokens == 0
        assert response.total_tokens == 0
        assert response.latency_ms == 0.0

    def test_rejects_negative_token_counts(self):
        with pytest.raises(ValidationError):
            AIResponse(content="hi", model="m", prompt_tokens=-1)

    def test_rejects_negative_latency(self):
        with pytest.raises(ValidationError):
            AIResponse(content="hi", model="m", latency_ms=-0.5)


class TestResponseFormat:
    def test_enum_values(self):
        assert ResponseFormat.TEXT == "text"
        assert ResponseFormat.JSON == "json_object"


class TestProviderAbstraction:
    def test_reference_implementation_satisfies_protocol(self, sample_response):
        provider = EchoProvider(sample_response)
        assert isinstance(provider, AIProvider)

    async def test_reference_implementation_interface(self, sample_response):
        provider = EchoProvider(sample_response)
        messages = [
            AIMessage(role="system", content="You are helpful."),
            AIMessage(role="user", content="Summarize."),
        ]
        result = await provider.generate(
            messages, temperature=0.5, max_tokens=64, response_format=ResponseFormat.JSON
        )
        assert result == sample_response
        assert provider.calls[0]["messages"] == messages
        assert provider.calls[0]["temperature"] == 0.5
        assert provider.calls[0]["max_tokens"] == 64
        assert provider.calls[0]["response_format"] == ResponseFormat.JSON

    def test_groq_provider_satisfies_protocol(self, groq_settings: Settings):
        provider = GroqProvider(groq_settings)
        assert isinstance(provider, AIProvider)

    def test_groq_provider_reads_model_from_settings(self, groq_settings: Settings):
        provider = GroqProvider(groq_settings)
        assert provider.model == "llama-3.3-70b-versatile"
