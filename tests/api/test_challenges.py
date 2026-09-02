import uuid
import pytest
from httpx import AsyncClient
from app.core.constants import ChallengeStatus, DifficultyLevel
from app.models.challenge import Challenge
from app.models.challenge_skill import ChallengeSkill
from app.models.skill import Skill
from tests.conftest import TestingSessionLocal


@pytest.fixture
async def seed_challenge_data():
    async with TestingSessionLocal() as session:
        skill1 = Skill(
            id=uuid.UUID("11111111-3333-5555-7777-999999999999"),
            name="React Architecture",
            category="Frontend",
        )
        skill2 = Skill(
            id=uuid.UUID("22222222-4444-6666-8888-000000000000"),
            name="TypeScript Mastery",
            category="Frontend",
        )
        session.add_all([skill1, skill2])
        await session.flush()

        published_challenge = Challenge(
            id=uuid.UUID("aaaaaaaa-3333-4444-5555-666666666666"),
            title="Real-Time Analytics Dashboard",
            description="Build a high-performance analytics UI.",
            instructions="Implement state management and WebSocket client.",
            difficulty=DifficultyLevel.INTERMEDIATE,
            status=ChallengeStatus.PUBLISHED,
        )
        session.add(published_challenge)
        await session.flush()

        cs1 = ChallengeSkill(
            challenge_id=published_challenge.id,
            skill_id=skill1.id,
            importance_weight=1.0,
        )
        cs2 = ChallengeSkill(
            challenge_id=published_challenge.id,
            skill_id=skill2.id,
            importance_weight=0.8,
        )
        session.add_all([cs1, cs2])

        draft_challenge = Challenge(
            id=uuid.UUID("bbbbbbbb-3333-4444-5555-666666666666"),
            title="Draft Internal Prototype Challenge",
            difficulty=DifficultyLevel.ADVANCED,
            status=ChallengeStatus.DRAFT,
        )
        session.add(draft_challenge)
        await session.commit()


@pytest.mark.asyncio
async def test_list_challenges_public(async_client: AsyncClient, seed_challenge_data):
    response = await async_client.get("/api/v1/challenges")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Real-Time Analytics Dashboard"


@pytest.mark.asyncio
async def test_get_challenge_detail_with_skills(async_client: AsyncClient, seed_challenge_data):
    challenge_id = "aaaaaaaa-3333-4444-5555-666666666666"
    response = await async_client.get(f"/api/v1/challenges/{challenge_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Real-Time Analytics Dashboard"
    assert len(data["skills"]) == 2
    skill_names = [s["skill_name"] for s in data["skills"]]
    assert "React Architecture" in skill_names
    assert "TypeScript Mastery" in skill_names


@pytest.mark.asyncio
async def test_create_challenge_employer_success(
    async_client: AsyncClient,
    employer_token: str,
    seed_challenge_data,
):
    payload = {
        "title": "Production API Gateway Challenge",
        "description": "Design an async API Gateway with rate limiting.",
        "difficulty": "advanced",
        "status": "published",
        "skills": [
            {
                "skill_id": "11111111-3333-5555-7777-999999999999",
                "importance_weight": 0.9,
            }
        ],
    }
    response = await async_client.post(
        "/api/v1/challenges",
        headers={"Authorization": f"Bearer {employer_token}"},
        json=payload,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Production API Gateway Challenge"
    assert data["difficulty"] == "advanced"


@pytest.mark.asyncio
async def test_create_challenge_learner_forbidden(
    async_client: AsyncClient,
    learner_token: str,
):
    payload = {
        "title": "Unauthorized Learner Challenge",
        "difficulty": "beginner",
    }
    response = await async_client.post(
        "/api/v1/challenges",
        headers={"Authorization": f"Bearer {learner_token}"},
        json=payload,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"
