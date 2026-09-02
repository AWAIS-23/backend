import uuid
import pytest
from httpx import AsyncClient
from app.core.constants import EvidenceSourceType, EvidenceStatus
from app.models.evidence import Evidence
from app.models.skill import Skill
from tests.conftest import TestingSessionLocal


@pytest.fixture
async def seed_evidence_data():
    async with TestingSessionLocal() as session:
        skill = Skill(
            id=uuid.UUID("77777777-8888-9999-0000-111111111111"),
            name="API Security",
            category="Security",
        )
        session.add(skill)
        await session.flush()

        evidence = Evidence(
            id=uuid.UUID("99999999-aaaa-bbbb-cccc-dddddddddddd"),
            profile_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            skill_id=skill.id,
            source_type=EvidenceSourceType.CHALLENGE_SUBMISSION,
            source_id=uuid.uuid4(),
            score=88.5,
            evidence_data={"project": "OAuth2 Implementation"},
            status=EvidenceStatus.PENDING,
        )
        session.add(evidence)
        await session.commit()


@pytest.mark.asyncio
async def test_verify_evidence_state_transitions(
    async_client: AsyncClient,
    admin_token: str,
    learner_token: str,
    seed_evidence_data,
):
    evidence_id = "99999999-aaaa-bbbb-cccc-dddddddddddd"

    # 1. Verifier approves evidence (pending -> verified)
    verify_res = await async_client.post(
        "/api/v1/verifications",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "evidence_id": evidence_id,
            "to_status": "verified",
            "notes": "Verified candidate code quality and adherence to RFC standards.",
        },
    )
    assert verify_res.status_code == 201
    assert verify_res.json()["to_status"] == "verified"
    assert verify_res.json()["from_status"] == "pending"

    # 2. Check evidence detail has verified status
    get_res = await async_client.get(
        f"/api/v1/evidence/{evidence_id}",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "verified"

    # 3. Invalid transition test: verified evidence cannot be reset to unverified or pending
    invalid_trans = await async_client.post(
        "/api/v1/verifications",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "evidence_id": evidence_id,
            "to_status": "pending",
            "notes": "Attempting illegal reversion.",
        },
    )
    assert invalid_trans.status_code == 400
    assert invalid_trans.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


@pytest.mark.asyncio
async def test_verification_audit_trail(
    async_client: AsyncClient,
    admin_token: str,
    learner_token: str,
    seed_evidence_data,
):
    evidence_id = "99999999-aaaa-bbbb-cccc-dddddddddddd"

    # Approve
    await async_client.post(
        "/api/v1/verifications",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "evidence_id": evidence_id,
            "to_status": "verified",
            "notes": "Audit note 1",
        },
    )

    # Fetch audit trail
    history_res = await async_client.get(
        f"/api/v1/verifications/evidence/{evidence_id}",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert history_res.status_code == 200
    trail = history_res.json()
    assert len(trail) == 1
    assert trail[0]["notes"] == "Audit note 1"
    assert trail[0]["to_status"] == "verified"
