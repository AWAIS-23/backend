"""
Unit tests for the skill_gap prompt specification.

Verifies:
- System instruction is present and constrains AI behavior.
- Match scores appear in trusted context.
- Skill breakdown appears in trusted context.
- Learner note is wrapped in <untrusted_data> delimiters.
- Empty/None learner note does NOT add untrusted section.
- Opportunity metadata is present in trusted context.
- Prompt never exposes credentials or internal identifiers.
"""
import pytest

from app.ai.prompts.skill_gap import (
    EXPLANATION_INSTRUCTIONS,
    SYSTEM_INSTRUCTION,
    build_skill_gap_prompt,
)


SAMPLE_MATCH_SUMMARY = {
    "overall_score": 72.5,
    "skill_score": 80.0,
    "evidence_score": 60.0,
    "experience_score": 50.0,
}

SAMPLE_SKILL_DETAILS = [
    {
        "skill_name": "Python",
        "weight": 0.5,
        "coverage": 100.0,
        "has_verified_evidence": True,
        "evidence_score": 100.0,
    },
    {
        "skill_name": "PostgreSQL",
        "weight": 0.2,
        "coverage": 0.0,
        "has_verified_evidence": False,
        "evidence_score": 0.0,
    },
]


class TestSystemInstruction:
    def test_system_instruction_defines_role(self):
        assert "career skills coach" in SYSTEM_INSTRUCTION
        assert "Rising Skills" in SYSTEM_INSTRUCTION

    def test_system_instruction_constrains_behavior(self):
        assert "authoritative" in SYSTEM_INSTRUCTION.lower()
        assert "never invent" in SYSTEM_INSTRUCTION.lower()
        assert "never alter" in SYSTEM_INSTRUCTION.lower()

    def test_system_instruction_prohibits_employment_claims(self):
        assert "employment guarantees" in SYSTEM_INSTRUCTION.lower()

    def test_system_instruction_limits_length(self):
        assert "concise" in SYSTEM_INSTRUCTION.lower() or "300 words" in SYSTEM_INSTRUCTION


class TestBuildPrompt:
    def test_returns_builder_with_two_messages(self):
        builder = build_skill_gap_prompt(
            match_summary=SAMPLE_MATCH_SUMMARY,
            skill_details=SAMPLE_SKILL_DETAILS,
            opportunity_title="Backend Engineer",
            opportunity_type="job",
        )
        messages = builder.build()
        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[1].role == "user"

    def test_system_message_contains_instruction(self):
        builder = build_skill_gap_prompt(
            match_summary=SAMPLE_MATCH_SUMMARY,
            skill_details=SAMPLE_SKILL_DETAILS,
            opportunity_title="Backend Engineer",
            opportunity_type="job",
        )
        messages = builder.build()
        system = messages[0].content
        assert "career skills coach" in system
        assert "STRICT RULES" in system

    def test_user_message_contains_match_scores(self):
        builder = build_skill_gap_prompt(
            match_summary=SAMPLE_MATCH_SUMMARY,
            skill_details=SAMPLE_SKILL_DETAILS,
            opportunity_title="Backend Engineer",
            opportunity_type="job",
        )
        messages = builder.build()
        user = messages[1].content
        assert "72.5" in user
        assert "80.0" in user
        assert "60.0" in user
        assert "50.0" in user

    def test_user_message_contains_skill_names(self):
        builder = build_skill_gap_prompt(
            match_summary=SAMPLE_MATCH_SUMMARY,
            skill_details=SAMPLE_SKILL_DETAILS,
            opportunity_title="Backend Engineer",
            opportunity_type="job",
        )
        messages = builder.build()
        user = messages[1].content
        assert "Python" in user
        assert "PostgreSQL" in user

    def test_user_message_contains_opportunity_metadata(self):
        builder = build_skill_gap_prompt(
            match_summary=SAMPLE_MATCH_SUMMARY,
            skill_details=SAMPLE_SKILL_DETAILS,
            opportunity_title="Senior Backend Role",
            opportunity_type="job",
        )
        messages = builder.build()
        user = messages[1].content
        assert "Senior Backend Role" in user
        assert "job" in user

    def test_explanation_instructions_added(self):
        builder = build_skill_gap_prompt(
            match_summary=SAMPLE_MATCH_SUMMARY,
            skill_details=SAMPLE_SKILL_DETAILS,
            opportunity_title="Backend Engineer",
            opportunity_type="job",
        )
        messages = builder.build()
        # The instructions should be present in either system or user message.
        combined = messages[0].content + messages[1].content
        for instr in EXPLANATION_INSTRUCTIONS:
            # At least a key part of each instruction should appear.
            key_phrase = instr[:30]
            assert key_phrase in combined, f"Missing instruction: {instr}"


class TestLearnerNoteHandling:
    def test_learner_note_in_untrusted_delimiters(self):
        builder = build_skill_gap_prompt(
            match_summary=SAMPLE_MATCH_SUMMARY,
            skill_details=SAMPLE_SKILL_DETAILS,
            opportunity_title="Backend Engineer",
            opportunity_type="job",
            learner_note="I want to focus on database skills.",
        )
        messages = builder.build()
        user = messages[1].content
        assert "<untrusted_data>" in user
        assert "</untrusted_data>" in user
        assert "I want to focus on database skills." in user

    def test_learner_note_not_in_system_message(self):
        builder = build_skill_gap_prompt(
            match_summary=SAMPLE_MATCH_SUMMARY,
            skill_details=SAMPLE_SKILL_DETAILS,
            opportunity_title="Backend Engineer",
            opportunity_type="job",
            learner_note="Focus on my weaknesses please.",
        )
        messages = builder.build()
        system = messages[0].content
        assert "Focus on my weaknesses please." not in system

    def test_none_learner_note_no_untrusted_section(self):
        builder = build_skill_gap_prompt(
            match_summary=SAMPLE_MATCH_SUMMARY,
            skill_details=SAMPLE_SKILL_DETAILS,
            opportunity_title="Backend Engineer",
            opportunity_type="job",
            learner_note=None,
        )
        messages = builder.build()
        user = messages[1].content
        # When no learner_note, there should be no <untrusted_data> section
        # unless other untrusted content is added (there isn't).
        assert "<untrusted_data>" not in user

    def test_empty_learner_note_no_untrusted_section(self):
        builder = build_skill_gap_prompt(
            match_summary=SAMPLE_MATCH_SUMMARY,
            skill_details=SAMPLE_SKILL_DETAILS,
            opportunity_title="Backend Engineer",
            opportunity_type="job",
            learner_note="   ",
        )
        messages = builder.build()
        user = messages[1].content
        assert "<untrusted_data>" not in user


class TestSecurityProperties:
    def test_no_api_key_in_prompt(self):
        builder = build_skill_gap_prompt(
            match_summary=SAMPLE_MATCH_SUMMARY,
            skill_details=SAMPLE_SKILL_DETAILS,
            opportunity_title="Backend Engineer",
            opportunity_type="job",
            learner_note="test",
        )
        messages = builder.build()
        for msg in messages:
            assert "GROQ_API_KEY" not in msg.content
            assert "Bearer " not in msg.content
            assert "eyJ" not in msg.content

    def test_no_jwt_or_auth_material(self):
        builder = build_skill_gap_prompt(
            match_summary=SAMPLE_MATCH_SUMMARY,
            skill_details=SAMPLE_SKILL_DETAILS,
            opportunity_title="Backend Engineer",
            opportunity_type="job",
        )
        messages = builder.build()
        for msg in messages:
            assert "Authorization" not in msg.content
            assert "password" not in msg.content.lower()

    def test_no_skill_id_in_sanitized_prompt(self):
        """When the service strips skill_id before calling the prompt builder,
        the UUID must not appear in the rendered AI prompt."""
        sanitized_details = [
            {
                "skill_name": "Python",
                "weight": 0.5,
                "coverage": 100.0,
                "has_verified_evidence": True,
                "evidence_score": 100.0,
            },
        ]
        builder = build_skill_gap_prompt(
            match_summary=SAMPLE_MATCH_SUMMARY,
            skill_details=sanitized_details,
            opportunity_title="Backend Engineer",
            opportunity_type="job",
        )
        messages = builder.build()
        for msg in messages:
            assert "skill_id" not in msg.content
        # Skill names remain present in the user message for the AI.
        user_content = messages[1].content
        assert "Python" in user_content
