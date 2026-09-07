"""
app/ai/prompts/challenge_hint.py
-------------------------------
Prompt specification for AI Challenge Hints.

Helps learners get guidance on how to approach a practical challenge
without giving away the solution.
"""
from app.ai.prompts.base import PromptBuilder

SYSTEM_INSTRUCTION = (
    "You are a technical mentor for the Rising Skills platform. "
    "Your role is to help learners approach practical challenges by "
    "providing guidance, hints, and strategic advice.\n\n"
    "STRICT RULES:\n"
    "- Never provide direct solutions, code, or complete answers.\n"
    "- Never reveal evaluation criteria or rubric details.\n"
    "- Provide conceptual guidance and suggest approaches.\n"
    "- Encourage independent problem-solving.\n"
    "- Keep the hint concise (under 250 words), structured, and actionable.\n"
    "- Frame suggestions as 'you might consider' rather than 'you should'."
)

HINT_INSTRUCTIONS = [
    "Break down the challenge into logical steps or phases.",
    "Suggest 2-3 key concepts or techniques the learner should review.",
    "Mention common pitfalls or mistakes to avoid.",
    "Provide a high-level approach without writing actual code.",
]


def build_challenge_hint_prompt(
    challenge_title: str,
    challenge_description: str | None,
    challenge_instructions: str | None,
    difficulty: str,
    skills: list[str],
    learner_note: str | None = None,
) -> PromptBuilder:
    builder = PromptBuilder(system=SYSTEM_INSTRUCTION)

    for instruction in HINT_INSTRUCTIONS:
        builder.add_instruction(instruction)

    builder.add_context(
        "challenge",
        {
            "title": challenge_title,
            "description": challenge_description or "",
            "instructions": challenge_instructions or "",
            "difficulty": difficulty,
            "skills_tested": skills,
        },
    )

    if learner_note and learner_note.strip():
        builder.add_user_input("learner_question", learner_note.strip())

    return builder
