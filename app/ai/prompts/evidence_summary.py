"""
app/ai/prompts/evidence_summary.py
---------------------------------
Prompt specification for AI Evidence Summary.

Provides learners with an AI-generated narrative summary of their
evidence portfolio, highlighting strengths and areas for improvement.
"""
from app.ai.prompts.base import PromptBuilder

SYSTEM_INSTRUCTION = (
    "You are a skills development coach for the Rising Skills platform. "
    "Your role is to help learners understand their evidence portfolio "
    "and identify strengths and growth areas.\n\n"
    "STRICT RULES:\n"
    "- The platform data provided to you is authoritative and final.\n"
    "- Never invent, estimate, or assume scores or evidence not present.\n"
    "- Never claim a skill is 'mastered' or 'certified' unless verified.\n"
    "- Frame suggestions as 'you might consider' rather than 'you must'.\n"
    "- Keep the summary concise (under 300 words), structured, and encouraging."
)

SUMMARY_INSTRUCTIONS = [
    "Start with a brief overview of the learner's evidence portfolio.",
    "Highlight verified strengths and well-evidenced skills.",
    "Identify skills with weak or no evidence as growth opportunities.",
    "Suggest 1-2 concrete next steps to strengthen the portfolio.",
    "End with an encouraging closing statement.",
]


def build_evidence_summary_prompt(
    evidence_items: list[dict],
    skill_names: dict[str, str] | None = None,
    learner_note: str | None = None,
) -> PromptBuilder:
    builder = PromptBuilder(system=SYSTEM_INSTRUCTION)

    for instruction in SUMMARY_INSTRUCTIONS:
        builder.add_instruction(instruction)

    # Enrich evidence items with skill names if available
    enriched = []
    for item in evidence_items:
        skill_name = "Unknown"
        if skill_names and item.get("skill_id") in skill_names:
            skill_name = skill_names[item["skill_id"]]
        enriched.append({
            "skill_name": skill_name,
            "source_type": item.get("source_type", "unknown"),
            "status": item.get("status", "unknown"),
            "score": item.get("score", 0),
        })

    builder.add_context("evidence_portfolio", enriched)

    if learner_note and learner_note.strip():
        builder.add_user_input("learner_focus", learner_note.strip())

    return builder
