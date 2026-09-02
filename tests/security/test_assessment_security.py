import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from app.core.constants import AssessmentStatus, AttemptStatus, DifficultyLevel
from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt
from app.models.assessment_question import AssessmentQuestion
from app.models.skill import Skill
from tests.conftest import TestingSessionLocal


@pytest.fixture
async def seed_security_assessment():
    async with TestingSessionLocal() as session:
        skill = Skill(
            id=uuid.UUID("33333333-4444-5555-6666-777777777777"),
            name="Security Engineering",
            category="Cybersecurity",
        )
        session.add(skill)
        await session.flush()

        assessment1 = Assessment(
            id=uuid.UUID("11111111-9999-8888-7777-666666666666"),
            title="AppSec Fundamentals",
            skill_id=skill.id,
            difficulty=DifficultyLevel.BEGINNER,
            duration_seconds=60,  # 1 minute
            passing_score=70,
            status=AssessmentStatus.PUBLISHED,
        )
        assessment2 = Assessment(
            id=uuid.UUID("22222222-9999-8888-7777-666666666666"),
            title="Network Security Exam",
            skill_id=skill.id,
            difficulty=DifficultyLevel.ADVANCED,
            duration_seconds=60,
            passing_score=70,
            status=AssessmentStatus.PUBLISHED,
        )
        session.add_all([assessment1, assessment2])
        await session.flush()

        q_a1 = AssessmentQuestion(
            id=uuid.UUID("aaaa1111-bbbb-cccc-dddd-eeeeeeeeeeee"),
            assessment_id=assessment1.id,
            question_text="What does XSS stand for?",
            options=[{"id": "a", "text": "Cross-Site Scripting"}, {"id": "b", "text": "Cross-Site Style"}],
            correct_answer="a",
            points=10,
            display_order=1,
        )
        q_a2 = AssessmentQuestion(
            id=uuid.UUID("aaaa2222-bbbb-cccc-dddd-eeeeeeeeeeee"),
            assessment_id=assessment2.id,
            question_text="What port does HTTPS use?",
            options=[{"id": "a", "text": "80"}, {"id": "b", "text": "443"}],
            correct_answer="b",
            points=10,
            display_order=1,
        )
        session.add_all([q_a1, q_a2])
        await session.commit()


@pytest.mark.asyncio
async def test_idor_cross_user_attempt_tampering(
    async_client: AsyncClient,
    learner_token: str,
    learner_token_2: str,
    seed_security_assessment,
):
    """Learner 2 cannot submit answers or results for Learner 1's attempt."""
    assessment_id = "11111111-9999-8888-7777-666666666666"

    # Learner 1 starts attempt
    start_res = await async_client.post(
        f"/api/v1/assessments/{assessment_id}/attempts",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    attempt_id = start_res.json()["id"]

    # Learner 2 tries to submit an answer to Learner 1's attempt (IDOR attack)
    idor_ans = await async_client.post(
        f"/api/v1/attempts/{attempt_id}/answers",
        headers={"Authorization": f"Bearer {learner_token_2}"},
        json={"question_id": "aaaa1111-bbbb-cccc-dddd-eeeeeeeeeeee", "selected_option": "a"},
    )
    assert idor_ans.status_code == 403
    assert idor_ans.json()["error"]["code"] == "PERMISSION_DENIED"

    # Learner 2 tries to submit/finalize Learner 1's attempt
    idor_submit = await async_client.post(
        f"/api/v1/attempts/{attempt_id}/submit",
        headers={"Authorization": f"Bearer {learner_token_2}"},
    )
    assert idor_submit.status_code == 403
    assert idor_submit.json()["error"]["code"] == "PERMISSION_DENIED"

    # Learner 2 tries to view Learner 1's result
    # First finalize by Learner 1
    await async_client.post(
        f"/api/v1/attempts/{attempt_id}/submit",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    idor_view = await async_client.get(
        f"/api/v1/attempts/{attempt_id}/result",
        headers={"Authorization": f"Bearer {learner_token_2}"},
    )
    assert idor_view.status_code == 403
    assert idor_view.json()["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_foreign_question_injection_rejected(
    async_client: AsyncClient,
    learner_token: str,
    seed_security_assessment,
):
    """Submitting a question belonging to another assessment must be rejected with 400."""
    assessment_id = "11111111-9999-8888-7777-666666666666"

    start_res = await async_client.post(
        f"/api/v1/assessments/{assessment_id}/attempts",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    attempt_id = start_res.json()["id"]

    # Question from assessment 2
    foreign_q_id = "aaaa2222-bbbb-cccc-dddd-eeeeeeeeeeee"
    res = await async_client.post(
        f"/api/v1/attempts/{attempt_id}/answers",
        headers={"Authorization": f"Bearer {learner_token}"},
        json={"question_id": foreign_q_id, "selected_option": "b"},
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_QUESTION_FOR_ASSESSMENT"


@pytest.mark.asyncio
async def test_invalid_option_choice_rejected(
    async_client: AsyncClient,
    learner_token: str,
    seed_security_assessment,
):
    """Submitting an option ID that does not exist for the question is rejected with 400."""
    assessment_id = "11111111-9999-8888-7777-666666666666"

    start_res = await async_client.post(
        f"/api/v1/assessments/{assessment_id}/attempts",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    attempt_id = start_res.json()["id"]

    res = await async_client.post(
        f"/api/v1/attempts/{attempt_id}/answers",
        headers={"Authorization": f"Bearer {learner_token}"},
        json={"question_id": "aaaa1111-bbbb-cccc-dddd-eeeeeeeeeeee", "selected_option": "invalid_opt_z"},
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_OPTION_SELECTED"


@pytest.mark.asyncio
async def test_answer_after_finalized_attempt_rejected(
    async_client: AsyncClient,
    learner_token: str,
    seed_security_assessment,
):
    """Answers cannot be added or modified after attempt submission."""
    assessment_id = "11111111-9999-8888-7777-666666666666"

    start_res = await async_client.post(
        f"/api/v1/assessments/{assessment_id}/attempts",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    attempt_id = start_res.json()["id"]

    # Finalize
    await async_client.post(
        f"/api/v1/attempts/{attempt_id}/submit",
        headers={"Authorization": f"Bearer {learner_token}"},
    )

    # Attempt to modify answer after submission
    late_ans = await async_client.post(
        f"/api/v1/attempts/{attempt_id}/answers",
        headers={"Authorization": f"Bearer {learner_token}"},
        json={"question_id": "aaaa1111-bbbb-cccc-dddd-eeeeeeeeeeee", "selected_option": "a"},
    )
    assert late_ans.status_code == 400
    assert late_ans.json()["error"]["code"] == "ATTEMPT_NOT_IN_PROGRESS"
