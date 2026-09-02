import uuid
import pytest
from httpx import AsyncClient
from app.core.constants import AssessmentStatus, DifficultyLevel
from app.models.assessment import Assessment
from app.models.assessment_question import AssessmentQuestion
from app.models.skill import Skill
from tests.conftest import TestingSessionLocal


@pytest.fixture
async def seed_assessment_data():
    async with TestingSessionLocal() as session:
        # Create a skill
        skill = Skill(
            id=uuid.UUID("11111111-2222-3333-4444-555555555555"),
            name="Cloud Architecture",
            category="Infrastructure",
        )
        session.add(skill)
        await session.flush()

        # Create published assessment
        published_assessment = Assessment(
            id=uuid.UUID("aaaaaaaa-1111-2222-3333-444444444444"),
            title="Cloud Architecture Certification Exam",
            description="Evaluates production cloud infrastructure principles.",
            skill_id=skill.id,
            difficulty=DifficultyLevel.INTERMEDIATE,
            duration_seconds=1800,
            passing_score=75,
            status=AssessmentStatus.PUBLISHED,
        )
        session.add(published_assessment)
        await session.flush()

        # Add questions with correct answers
        q1 = AssessmentQuestion(
            id=uuid.UUID("bbbbbbbb-1111-2222-3333-444444444444"),
            assessment_id=published_assessment.id,
            question_text="Which cloud deployment model offers dedicated resources to a single organization?",
            options=[
                {"id": "a", "text": "Public Cloud"},
                {"id": "b", "text": "Private Cloud"},
                {"id": "c", "text": "Community Cloud"},
                {"id": "d", "text": "Hybrid Cloud"},
            ],
            correct_answer="b",
            points=10,
            display_order=1,
            explanation="Private cloud infrastructure is provisioned for exclusive use by a single organization.",
        )
        q2 = AssessmentQuestion(
            id=uuid.UUID("cccccccc-1111-2222-3333-444444444444"),
            assessment_id=published_assessment.id,
            question_text="What provides high availability across geographical regions?",
            options=[
                {"id": "a", "text": "Single Availability Zone"},
                {"id": "b", "text": "Multi-Region Redundancy"},
            ],
            correct_answer="b",
            points=10,
            display_order=2,
            explanation="Multi-region deployments protect against regional failures.",
        )
        session.add_all([q1, q2])

        # Create draft assessment (should be hidden from normal learners)
        draft_assessment = Assessment(
            id=uuid.UUID("dddddddd-1111-2222-3333-444444444444"),
            title="Draft Internal Quiz",
            description="Work in progress.",
            skill_id=skill.id,
            status=AssessmentStatus.DRAFT,
        )
        session.add(draft_assessment)
        await session.commit()


@pytest.mark.asyncio
async def test_list_assessments_shows_only_published(async_client: AsyncClient, seed_assessment_data):
    response = await async_client.get("/api/v1/assessments")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Cloud Architecture Certification Exam"
    assert data["items"][0]["status"] == "published"


@pytest.mark.asyncio
async def test_get_assessment_detail_masks_correct_answers(async_client: AsyncClient, seed_assessment_data):
    assessment_id = "aaaaaaaa-1111-2222-3333-444444444444"
    response = await async_client.get(f"/api/v1/assessments/{assessment_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Cloud Architecture Certification Exam"
    assert len(data["questions"]) == 2

    # SECURITY AUDIT: Verify no answer keys or explanations are leaked
    for q in data["questions"]:
        assert "correct_answer" not in q
        assert "is_correct" not in q
        assert "explanation" not in q
        assert "answer_key" not in q
        assert len(q["options"]) >= 2
        for opt in q["options"]:
            assert "is_correct" not in opt


@pytest.mark.asyncio
async def test_get_draft_assessment_forbidden_for_learner(async_client: AsyncClient, seed_assessment_data):
    draft_id = "dddddddd-1111-2222-3333-444444444444"
    response = await async_client.get(f"/api/v1/assessments/{draft_id}")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"
