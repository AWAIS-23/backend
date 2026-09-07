"""
Unit tests for AIService orchestration using a fully fake provider.
No real Groq API calls are ever made.
"""
import pytest
from pydantic import BaseModel

from app.ai.exceptions import AIInvalidResponseError, AIProviderError, AITimeoutError
from app.ai.prompts.base import PromptBuilder
from app.ai.schemas import AIResponse, ResponseFormat
from app.ai.service import AIService


class FakeProvider:
    """Deterministic in-memory AIProvider double recording every call."""

    def __init__(self, response: AIResponse | None = None, error: Exception | None = None):
        self.response = response or AIResponse(content="{}", model="fake-model")
        self.error = error
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
        if self.error is not None:
            raise self.error
        return self.response


class SampleOutput(BaseModel):
    summary: str
    score: int


@pytest.fixture
def prompt() -> PromptBuilder:
    return (
        PromptBuilder(system="You are a skills coach.")
        .add_context("match", {"overall_score": 72.5})
        .add_user_input("cover_note", "I love building APIs.")
    )


def make_response(content: str) -> AIResponse:
    return AIResponse(content=content, model="fake-model", total_tokens=10)


class TestComplete:
    async def test_provider_called_with_built_messages(self, prompt: PromptBuilder):
        provider = FakeProvider(response=make_response("Nice work."))
        service = AIService(provider)

        result = await service.complete(prompt, feature="unit-test")

        assert result.content == "Nice work."
        assert len(provider.calls) == 1
        messages = provider.calls[0]["messages"]
        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[1].role == "user"
        assert "You are a skills coach." in messages[0].content
        assert '{"overall_score": 72.5}' in messages[1].content

    async def test_overrides_forwarded_to_provider(self, prompt: PromptBuilder):
        provider = FakeProvider(response=make_response("ok"))
        service = AIService(provider)

        await service.complete(prompt, feature="unit-test", temperature=0.7, max_tokens=256)

        assert provider.calls[0]["temperature"] == 0.7
        assert provider.calls[0]["max_tokens"] == 256

    async def test_typed_provider_errors_propagate(self, prompt: PromptBuilder):
        provider = FakeProvider(error=AITimeoutError())
        service = AIService(provider)

        with pytest.raises(AITimeoutError):
            await service.complete(prompt, feature="unit-test")

    async def test_unexpected_provider_error_wrapped(self, prompt: PromptBuilder):
        provider = FakeProvider(error=RuntimeError("boom"))
        service = AIService(provider)

        with pytest.raises(AIProviderError) as exc_info:
            await service.complete(prompt, feature="unit-test")
        assert exc_info.value.__cause__ is not None

    async def test_invalid_temperature_rejected_before_provider_call(self, prompt: PromptBuilder):
        provider = FakeProvider(response=make_response("ok"))
        service = AIService(provider)

        with pytest.raises(ValueError):
            await service.complete(prompt, feature="unit-test", temperature=5.0)
        assert provider.calls == []

    async def test_invalid_max_tokens_rejected_before_provider_call(self, prompt: PromptBuilder):
        provider = FakeProvider(response=make_response("ok"))
        service = AIService(provider)

        with pytest.raises(ValueError):
            await service.complete(prompt, feature="unit-test", max_tokens=0)
        assert provider.calls == []


class TestGenerateStructured:
    async def test_valid_json_validated_against_model(self, prompt: PromptBuilder):
        content = '{"summary": "Strong Python fundamentals.", "score": 88}'
        provider = FakeProvider(response=make_response(content))
        service = AIService(provider)

        result = await service.generate_structured(
            prompt, feature="unit-test", response_model=SampleOutput
        )

        assert isinstance(result, SampleOutput)
        assert result.summary == "Strong Python fundamentals."
        assert result.score == 88

    async def test_json_response_format_requested(self, prompt: PromptBuilder):
        provider = FakeProvider(response=make_response('{"summary": "s", "score": 1}'))
        service = AIService(provider)

        await service.generate_structured(
            prompt, feature="unit-test", response_model=SampleOutput
        )

        assert provider.calls[0]["response_format"] == ResponseFormat.JSON

    async def test_fenced_json_tolerated(self, prompt: PromptBuilder):
        content = '```json\n{"summary": "fenced", "score": 5}\n```'
        provider = FakeProvider(response=make_response(content))
        service = AIService(provider)

        result = await service.generate_structured(
            prompt, feature="unit-test", response_model=SampleOutput
        )
        assert result.summary == "fenced"

    async def test_malformed_json_rejected(self, prompt: PromptBuilder):
        provider = FakeProvider(response=make_response("this is not json"))
        service = AIService(provider)

        with pytest.raises(AIInvalidResponseError) as exc_info:
            await service.generate_structured(
                prompt, feature="unit-test", response_model=SampleOutput
            )
        assert exc_info.value.__cause__ is not None
        assert "malformed JSON" in exc_info.value.message

    async def test_schema_violation_rejected(self, prompt: PromptBuilder):
        # Missing required field 'score'.
        provider = FakeProvider(response=make_response('{"summary": "no score"}'))
        service = AIService(provider)

        with pytest.raises(AIInvalidResponseError) as exc_info:
            await service.generate_structured(
                prompt, feature="unit-test", response_model=SampleOutput
            )
        assert "expected schema" in exc_info.value.message

    async def test_non_object_json_rejected(self, prompt: PromptBuilder):
        provider = FakeProvider(response=make_response('["just", "a", "list"]'))
        service = AIService(provider)

        with pytest.raises(AIInvalidResponseError):
            await service.generate_structured(
                prompt, feature="unit-test", response_model=SampleOutput
            )

    async def test_provider_failure_propagates_before_parsing(self, prompt: PromptBuilder):
        provider = FakeProvider(error=AITimeoutError())
        service = AIService(provider)

        with pytest.raises(AITimeoutError):
            await service.generate_structured(
                prompt, feature="unit-test", response_model=SampleOutput
            )


class TestConstruction:
    def test_requires_provider(self):
        with pytest.raises(ValueError):
            AIService(None)
