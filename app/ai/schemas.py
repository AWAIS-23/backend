"""
app/ai/schemas.py
-----------------
Provider-independent Pydantic schemas forming the stable contract between
the AI service layer and provider implementations.

SECURITY: Provider-specific SDK objects must never escape a provider
implementation. Everything crossing the provider boundary is expressed
through these neutral schemas.
"""
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class AIMessage(BaseModel):
    """
    A single chat message in a provider-neutral format.

    The role/content structure maps cleanly onto every mainstream chat
    completion API without leaking vendor-specific types.
    """
    role: Literal["system", "user", "assistant"]
    content: str


class ResponseFormat(StrEnum):
    """
    Generic response formatting modes understood by the provider layer.

    Providers translate these values into their native structured-output
    syntax (e.g. Groq's ``{"type": "json_object"}``).
    """
    TEXT = "text"
    JSON = "json_object"


class AIResponse(BaseModel):
    """
    Provider-independent outcome of a single AI generation call.

    Contains the generated content plus the operational metadata useful
    for logging and cost monitoring. Token counts default to zero because
    not every provider reliably reports usage.
    """
    content: str = Field(..., description="Generated text content")
    model: str = Field(..., description="Model that produced the content")
    prompt_tokens: int = Field(default=0, ge=0, description="Tokens consumed by the prompt")
    completion_tokens: int = Field(default=0, ge=0, description="Tokens produced by the model")
    total_tokens: int = Field(default=0, ge=0, description="Total tokens for the call")
    latency_ms: float = Field(default=0.0, ge=0.0, description="End-to-end call latency in milliseconds")
