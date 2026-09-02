import uuid
import pytest
from httpx import AsyncClient
from app.core.constants import AssessmentStatus, DifficultyLevel
from app.models.assessment import Assessment
from app.models.assessment_question import AssessmentQuestion
from app.models.skill import Skill
from tests.conftest import TestingSessionLocal


@pytest.fixture
async def seed_lifecycle_assessment():
    async with TestingSessionLocal() as session:
        skill = Skill(
            id=uuid.UUID("22222222-3333-4444-5555-666666666666"),
            name="Python Backend",
            category="Programming",
        )
        session.add(skill)
        await session.flush()

        assessment = Assessment(
            id=uuid.UUID("eeeeeeee-2222-3333-4444-555555555555"),
            title="FastAPI Mastery Test",
            skill_id=skill.id,
            difficulty=DifficultyLevel.INTERMEDIATE,
            duration_seconds=1200,
            passing_score=70,  # 70%
            status=AssessmentStatus.PUBLISHED,
        )
        session.add(assessment)
        await session.flush()

        q1 = AssessmentQuestion(
            id=uuid.UUID("11111111-aaaa-bbbb-cccc-dddddddddddd"),
            assessment_id=assessment.id,
            question_text="Which decorator is used for GET endpoints in FastAPI?",
            options=[
                {"id": "a", "text": "@app.get()"},
                {"id": "b", "text": "@app.post()"},
                {"id": "c", "text": "@app.route()"},
            ],
            correct_answer="a",
            points=10,
            display_order=1,
        )
        q2 = AssessmentQuestion(
            id=uuid.UUID("22222222-aaaa-bbbb-cccc-dddddddddddd"),
            assessment_id=assessment.id,
            question_text="What dependency is used for automatic request validation in FastAPI?",
            options=[
                {"id": "a", "text": "Marshmallow"},
                {"id": "b", "text": "Pydantic"},
                {"id": "c", "text": "Cerberus"},
            ],
            correct_answer="b",
            points=10,
            display_order=2,
        )
        session.add_all([q1, q2])
        await session.commit()


@pytest.mark.asyncio
async def test_full_assessment_lifecycle_pass(
    async_client: AsyncClient,
    learner_token: str,
    seed_lifecycle_assessment,
):
    assessment_id = "eeeeeeee-2222-3333-4444-555555555555"

    # 1. Start Attempt
    start_res = await async_client.post(
        f"/api/v1/assessments/{assessment_id}/attempts",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert start_res.status_code == 201
    start_data = start_res.json()
    attempt_id = start_data["id"]
    assert start_data["status"] == "in_progress"
    assert len(start_data["questions"]) == 2
    assert "expires_at" in start_data

    # 2. Submit Correct Answer for Q1
    q1_id = "11111111-aaaa-bbbb-cccc-dddddddddddd"
    ans1_res = await async_client.post(
        f"/api/v1/attempts/{attempt_id}/answers",
        headers={"Authorization": f"Bearer {learner_token}"},
        json={"question_id": q1_id, "selected_option": "a"},
    )
    assert ans1_res.status_code == 200
    ans1_data = ans1_res.json()
    assert ans1_data["attempt_id"] == attempt_id
    assert "is_correct" not in ans1_data  # Strict anti-leakage

    # 3. Submit Correct Answer for Q2
    q2_id = "22222222-aaaa-bbbb-cccc-dddddddddddd"
    ans2_res = await async_client.post(
        f"/api/v1/attempts/{attempt_id}/answers",
        headers={"Authorization": f"Bearer {learner_token}"},
        json={"question_id": q2_id, "selected_option": "b"},
    )
    assert ans2_res.status_code == 200

    # 4. Finalize & Submit Attempt
    submit_res = await async_client.post(
        f"/api/v1/attempts/{attempt_id}/submit",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert submit_res.status_code == 200
    result_data = submit_res.json()
    assert result_data["total_questions"] == 2
    assert result_data["answered_questions"] == 2
    assert result_data["correct_answers"] == 2
    assert result_data["earned_points"] == 20
    assert result_data["total_points"] == 20
    assert result_data["score_percentage"] == 100.0
    assert result_data["passed"] is True

    # 5. Fetch Result via GET
    get_res = await async_client.get(
        f"/api/v1/attempts/{attempt_id}/result",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert get_res.status_code == 200
    assert get_res.json()["score_percentage"] == 100.0


@pytest.mark.asyncio
async def test_duplicate_submission_idempotency(
    async_client: AsyncClient,
    learner_token: str,
    seed_lifecycle_assessment,
):
    assessment_id = "eeeeeeee-2222-3333-4444-555555555555"

    # Start attempt
    start_res = await async_client.post(
        f"/api/v1/assessments/{assessment_id}/attempts",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    attempt_id = start_res.json()["id"]

    # Submit Q1 (Incorrect) & Q2 (Correct) -> 10/20 = 50% -> Fail (Passing is 70%)
    await async_client.post(
        f"/api/v1/attempts/{attempt_id}/answers",
        headers={"Authorization": f"Bearer {learner_token}"},
        json={"question_id": "11111111-aaaa-bbbb-cccc-dddddddddddd", "selected_option": "b"},
    )
    await async_client.post(
        f"/api/v1/attempts/{attempt_id}/answers",
        headers={"Authorization": f"Bearer {learner_token}"},
        json={"question_id": "22222222-aaaa-bbbb-cccc-dddddddddddd", "selected_option": "b"},
    )

    # First submit
    sub1 = await async_client.post(
        f"/api/v1/attempts/{attempt_id}/submit",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert sub1.status_code == 200
    res1 = sub1.json()
    assert res1["correct_answers"] == 1
    assert res1["score_percentage"] == 50.0
    assert res1["passed"] is False

    # Second submit (Idempotent replay)
    sub2 = await async_client.post(
        f"/api/v1/attempts/{attempt_id}/submit",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert sub2.status_code == 200
    res2 = sub2.json()
    assert res2["id"] == res1["id"]
    assert res2["score_percentage"] == 50.0
