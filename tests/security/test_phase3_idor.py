import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from app.core.constants import ChallengeStatus, DifficultyLevel, EvidenceSourceType, EvidenceStatus, SubmissionStatus
from app.models.challenge import Challenge
from app.models.evidence import Evidence
from app.models.skill import Skill
from app.models.submission import Submission
from tests.conftest import TestingSessionLocal


@pytest.fixture
async def seed_idor_data():
    async with TestingSessionLocal() as session:
        skill = Skill(
            id=uuid.UUID("11110000-2222-3333-4444-555566667777"),
            name="Cloud Security",
            category="Security",
        )
        session.add(skill)
        await session.flush()

        challenge = Challenge(
            id=uuid.UUID("22220000-3333-4444-5555-666677778888"),
            title="IAM Policy Hardening",
            difficulty=DifficultyLevel.INTERMEDIATE,
            status=ChallengeStatus.PUBLISHED,
        )
        session.add(challenge)
        await session.flush()

        # Submission owned by Learner 1 (11111111-1111-1111-1111-111111111111)
        sub1 = Submission(
            id=uuid.UUID("33330000-4444-5555-6666-777788889999"),
            challenge_id=challenge.id,
            profile_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            repository_url="https://github.com/learner1/iam-policy",
            status=SubmissionStatus.SUBMITTED,
            submitted_at=datetime.now(timezone.utc),
        )
        session.add(sub1)

        # Evidence owned by Learner 1
        evi1 = Evidence(
            id=uuid.UUID("44440000-5555-6666-7777-888899990000"),
            profile_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            skill_id=skill.id,
            source_type=EvidenceSourceType.CHALLENGE_SUBMISSION,
            source_id=sub1.id,
            score=85.0,
            evidence_data={},
            status=EvidenceStatus.PENDING,
        )
        session.add(evi1)
        await session.commit()


@pytest.mark.asyncio
async def test_cross_user_submission_tampering_blocked(
    async_client: AsyncClient,
    learner_token_2: str,
    seed_idor_data,
):
    """Learner 2 cannot edit or view Learner 1's submission."""
    sub1_id = "33330000-4444-5555-6666-777788889999"

    # Learner 2 tries to PATCH Learner 1's submission
    patch_res = await async_client.patch(
        f"/api/v1/submissions/{sub1_id}",
        headers={"Authorization": f"Bearer {learner_token_2}"},
        json={"repository_url": "https://github.com/attacker/malicious"},
    )
    assert patch_res.status_code == 403
    assert patch_res.json()["error"]["code"] == "PERMISSION_DENIED"

    # Learner 2 tries to GET Learner 1's submission
    get_res = await async_client.get(
        f"/api/v1/submissions/{sub1_id}",
        headers={"Authorization": f"Bearer {learner_token_2}"},
    )
    assert get_res.status_code == 403
    assert get_res.json()["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_cross_user_evidence_access_blocked(
    async_client: AsyncClient,
    learner_token_2: str,
    seed_idor_data,
):
    """Learner 2 cannot view Learner 1's evidence record."""
    evi1_id = "44440000-5555-6666-7777-888899990000"

    res = await async_client.get(
        f"/api/v1/evidence/{evi1_id}",
        headers={"Authorization": f"Bearer {learner_token_2}"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_learner_cannot_self_verify_evidence(
    async_client: AsyncClient,
    learner_token: str,
    seed_idor_data,
):
    """Learner cannot call POST /verifications to verify their own evidence."""
    evi1_id = "44440000-5555-6666-7777-888899990000"

    res = await async_client.post(
        "/api/v1/verifications",
        headers={"Authorization": f"Bearer {learner_token}"},
        json={"evidence_id": evi1_id, "to_status": "verified"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "PERMISSION_DENIED"
