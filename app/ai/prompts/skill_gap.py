"""
app/ai/prompts/skill_gap.py
---------------------------
Prompt specification for the AI Skill Gap Explanation feature (Phase 6B).

Uses PromptBuilder to construct prompts with proper trusted/untrusted
separation. The system instruction constrains the AI to explain — never
decide — and treats the platform-supplied match data as authoritative.

ARCHITECTURAL RULE: This module generates prompts; it never computes
scores, reads databases, or accesses authentication context.
"""
from typing import Any

from app.ai.prompts.base import PromptBuilder

SYSTEM_INSTRUCTION = (
    "You are a career skills coach for the Rising Skills platform. "
    "Your role is to help learners understand their skill assessment results "
    "and match outcomes in clear, encouraging language.\n\n"
    "STRICT RULES:\n"
    "- The platform data provided to you is authoritative and final.\n"
    "- Never invent, estimate, or assume scores, evidence, or achievements "
    "that are not explicitly present in the supplied data.\n"
    "- Never alter, contradict, or reinterpret the numerical values provided.\n"
    "- Never claim a skill is 'mastered' or 'certified' unless the data "
    "explicitly states verification status is verified with a high score.\n"
    "- Never make employment guarantees or eligibility claims.\n"
    "- Never infer verification status that is not present.\n"
    "- If a skill has no verified evidence, state that clearly.\n"
    "- Frame suggestions as 'you might consider' rather than 'you must'.\n"
    "- Keep the explanation concise (under 300 words), structured, and "
    "suitable for a learner dashboard."
)

EXPLANATION_INSTRUCTIONS = [
    "Begin by summarizing the overall match result in one or two sentences.",
    "List strong skills (coverage >= 60% with verified evidence) first.",
    "Then address skill gaps (low coverage or no verified evidence).",
    "For each missing or weak skill, recommend 1-2 specific learning resources or courses (for example freeCodeCamp, Coursera, Khan Academy, MDN, or official docs) that would help the learner become eligible.",
    "End with a brief encouraging closing statement.",
]


def build_skill_gap_prompt(
    match_summary: dict[str, Any],
    skill_details: list[dict[str, Any]],
    opportunity_title: str,
    opportunity_type: str,
    learner_note: str | None = None,
) -> PromptBuilder:
    """
    Construct a PromptBuilder for the skill gap explanation feature.

    Args:
        match_summary: Deterministic composite scores from Match
            (overall_score, skill_score, evidence_score, experience_score).
        skill_details: Per-skill breakdown from Match.breakdown
            (skill_name, coverage, has_verified_evidence, evidence_score, weight).
        opportunity_title: The opportunity's human-readable title.
        opportunity_type: The opportunity type (job, internship, etc.).
        learner_note: Optional free-text focus area from the learner.
            Treated as untrusted input via add_user_input().

    Returns:
        A PromptBuilder ready for .build() → AIService.complete().
    """
    builder = PromptBuilder(system=SYSTEM_INSTRUCTION)

    for instruction in EXPLANATION_INSTRUCTIONS:
        builder.add_instruction(instruction)

    # Trusted platform context — rendered as JSON for machine readability.
    builder.add_context(
        "opportunity",
        {"title": opportunity_title, "type": opportunity_type},
    )
    builder.add_context(
        "match_scores",
        {
            "overall_score": match_summary.get("overall_score", 0.0),
            "skill_score": match_summary.get("skill_score", 0.0),
            "evidence_score": match_summary.get("evidence_score", 0.0),
            "experience_score": match_summary.get("experience_score", 0.0),
        },
    )
    builder.add_context("skill_breakdown", skill_details)

    # Untrusted learner input — wrapped in <untrusted_data> delimiters
    # and protected by the injection-defense directive.
    if learner_note and learner_note.strip():
        builder.add_user_input("learner_focus", learner_note.strip())

    return builder
