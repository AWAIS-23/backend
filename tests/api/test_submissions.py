import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from app.core.constants import ChallengeStatus, DifficultyLevel
from app.models.challenge import Challenge
from tests.conftest import TestingSessionLocal


@pytest.fixture
async def seed_submission_challenge():
    async with TestingSessionLocal() as session:
        active_challenge = Challenge(
            id=uuid.UUID("cccccccc-4444-5555-6666-777777777777"),
            title="Backend Service Implementation",
            difficulty=DifficultyLevel.INTERMEDIATE,
            status=ChallengeStatus.PUBLISHED,
            submission_deadline=datetime.now(timezone.utc) + timedelta(days=7),
        )
        expired_challenge = Challenge(
            id=uuid.UUID("dddddddd-4444-5555-6666-777777777777"),
            title="Past Hackathon Challenge",
            difficulty=DifficultyLevel.ADVANCED,
            status=ChallengeStatus.PUBLISHED,
            submission_deadline=datetime.now(timezone.utc) - timedelta(days=1),
        )
        session.add_all([active_challenge, expired_challenge])
        await session.commit()


@pytest.mark.asyncio
async def test_create_and_update_submission_success(
    async_client: AsyncClient,
    learner_token: str,
    seed_submission_challenge,
):
    challenge_id = "cccccccc-4444-5555-6666-777777777777"

    # 1. Create Submission
    submit_res = await async_client.post(
        f"/api/v1/challenges/{challenge_id}/submissions",
        headers={"Authorization": f"Bearer {learner_token}"},
        json={
            "repository_url": "https://github.com/learner/backend-service",
            "deployment_url": "https://service-demo.up.railway.app",
            "description": "Implemented with async SQLAlchemy and PostgreSQL.",
        },
    )
    assert submit_res.status_code == 201
    data = submit_res.json()
    submission_id = data["id"]
    assert data["status"] == "submitted"
    assert data["repository_url"] == "https://github.com/learner/backend-service"

    # 2. Get Submission Details
    get_res = await async_client.get(
        f"/api/v1/submissions/{submission_id}",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert get_res.status_code == 200
    assert get_res.json()["id"] == submission_id

    # 3. Update Submission Details
    patch_res = await async_client.patch(
        f"/api/v1/submissions/{submission_id}",
        headers={"Authorization": f"Bearer {learner_token}"},
        json={
            "deployment_url": "https://updated-demo.up.railway.app",
            "description": "Updated caching strategy using Redis.",
        },
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["deployment_url"] == "https://updated-demo.up.railway.app"


@pytest.mark.asyncio
async def test_submission_to_expired_challenge_rejected(
    async_client: AsyncClient,
    learner_token: str,
    seed_submission_challenge,
):
    expired_id = "dddddddd-4444-5555-6666-777777777777"
    response = await async_client.post(
        f"/api/v1/challenges/{expired_id}/submissions",
        headers={"Authorization": f"Bearer {learner_token}"},
        json={"repository_url": "https://github.com/learner/past-work"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "SUBMISSION_DEADLINE_PASSED"
