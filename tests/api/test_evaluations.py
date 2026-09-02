import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from app.core.constants import ChallengeStatus, DifficultyLevel, SubmissionStatus
from app.models.challenge import Challenge
from app.models.challenge_skill import ChallengeSkill
from app.models.skill import Skill
from app.models.submission import Submission
from tests.conftest import TestingSessionLocal


@pytest.fixture
async def seed_evaluation_data():
    async with TestingSessionLocal() as session:
        skill = Skill(
            id=uuid.UUID("55555555-6666-7777-8888-999999999999"),
            name="Distributed Systems",
            category="Backend",
        )
        session.add(skill)
        await session.flush()

        challenge = Challenge(
            id=uuid.UUID("eeeeeeee-5555-6666-7777-888888888888"),
            title="Consensus Algorithm Implementation",
            difficulty=DifficultyLevel.ADVANCED,
            status=ChallengeStatus.PUBLISHED,
        )
        session.add(challenge)
        await session.flush()

        cs = ChallengeSkill(
            challenge_id=challenge.id,
            skill_id=skill.id,
            importance_weight=1.0,
        )
        session.add(cs)
        await session.flush()

        # Learner submission (Learner 1: 11111111-1111-1111-1111-111111111111)
        sub = Submission(
            id=uuid.UUID("ffffffff-5555-6666-7777-888888888888"),
            challenge_id=challenge.id,
            profile_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            repository_url="https://github.com/learner/raft-consensus",
            status=SubmissionStatus.SUBMITTED,
            submitted_at=datetime.now(timezone.utc),
        )
        session.add(sub)
        await session.commit()


@pytest.mark.asyncio
async def test_evaluate_submission_and_create_evidence(
    async_client: AsyncClient,
    employer_token: str,
    learner_token: str,
    seed_evaluation_data,
):
    submission_id = "ffffffff-5555-6666-7777-888888888888"

    rubric_payload = {
        "rubric": [
            {"criterion": "Correctness of Leader Election", "max_points": 40, "awarded_points": 36},
            {"criterion": "Log Replication Performance", "max_points": 40, "awarded_points": 36},
            {"criterion": "Documentation & Tests", "max_points": 20, "awarded_points": 18},
        ],
        "feedback": "Outstanding implementation of Raft consensus protocol.",
    }

    # 1. Employer submits evaluation (Total 90/100 = 90.0%)
    eval_res = await async_client.post(
        f"/api/v1/submissions/{submission_id}/evaluations",
        headers={"Authorization": f"Bearer {employer_token}"},
        json=rubric_payload,
    )
    assert eval_res.status_code == 201
    eval_data = eval_res.json()
    assert eval_data["score"] == 90.0
    assert eval_data["submission_id"] == submission_id

    # 2. Verify submission status transitioned to EVALUATED
    sub_res = await async_client.get(
        f"/api/v1/submissions/{submission_id}",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert sub_res.status_code == 200
    assert sub_res.json()["status"] == "evaluated"

    # 3. Verify atomic Evidence creation for learner
    evidence_res = await async_client.get(
        "/api/v1/evidence",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert evidence_res.status_code == 200
    evi_data = evidence_res.json()
    assert evi_data["total"] >= 1
    created_evi = evi_data["items"][0]
    assert created_evi["score"] == 90.0
    assert created_evi["source_type"] == "challenge_submission"
    assert created_evi["status"] == "pending"


@pytest.mark.asyncio
async def test_self_evaluation_rejected(
    async_client: AsyncClient,
    learner_token: str,
    seed_evaluation_data,
):
    submission_id = "ffffffff-5555-6666-7777-888888888888"

    rubric_payload = {
        "rubric": [{"criterion": "Self Graded", "max_points": 100, "awarded_points": 100}],
    }
    response = await async_client.post(
        f"/api/v1/submissions/{submission_id}/evaluations",
        headers={"Authorization": f"Bearer {learner_token}"},
        json=rubric_payload,
    )
    # Learner role is forbidden from evaluating
    assert response.status_code == 403
