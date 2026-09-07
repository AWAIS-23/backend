"""
app/ai/prompts
--------------
Prompt construction infrastructure.

Feature-specific prompts (Phase 6B+) build on PromptBuilder without
duplicating injection-defense or untrusted-data plumbing.
"""
from app.ai.prompts.base import PromptBuilder

__all__ = ["PromptBuilder"]
