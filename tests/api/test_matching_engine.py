import uuid
import pytest
from httpx import AsyncClient
from app.core.constants import (
    EvidenceSourceType,
    EvidenceStatus,
    OpportunityStatus,
    OpportunityType,
)
from app.models.evidence import Evidence
from app.models.opportunity import Opportunity
from app.models.opportunity_skill import OpportunitySkill
from app.models.organization import Organization
from app.models.skill import Skill
from tests.conftest import TestingSessionLocal


@pytest.fixture
async def seed_matching_dataset():
    async with TestingSessionLocal() as session:
        # Organization
        org = Organization(
            id=uuid.UUID("99999999-0000-1111-2222-333333333333"),
            name="Scale AI Systems",
        )
        session.add(org)

        # Skills
        py_skill = Skill(
            id=uuid.UUID("11110000-1111-2222-3333-444455556666"),
            name="Python",
            category="Backend",
        )
        fastapi_skill = Skill(
            id=uuid.UUID("22220000-1111-2222-3333-444455556666"),
            name="FastAPI",
            category="Backend",
        )
        pg_skill = Skill(
            id=uuid.UUID("33330000-1111-2222-3333-444455556666"),
            name="PostgreSQL",
            category="Database",
        )
        session.add_all([py_skill, fastapi_skill, pg_skill])
        await session.flush()

        # Opportunity with weights: Python (0.5), FastAPI (0.3), PostgreSQL (0.2)
        opp = Opportunity(
            id=uuid.UUID("88888888-9999-0000-1111-222233334444"),
            organization_id=org.id,
            title="Principal Backend Engineer Role",
            opportunity_type=OpportunityType.JOB,
            status=OpportunityStatus.PUBLISHED,
        )
        session.add(opp)
        await session.flush()

        os1 = OpportunitySkill(opportunity_id=opp.id, skill_id=py_skill.id, importance_weight=0.5)
        os2 = OpportunitySkill(opportunity_id=opp.id, skill_id=fastapi_skill.id, importance_weight=0.3)
        os3 = OpportunitySkill(opportunity_id=opp.id, skill_id=pg_skill.id, importance_weight=0.2)
        session.add_all([os1, os2, os3])

        # Learner 1 (11111111-1111-1111-1111-111111111111) has verified evidence:
        # Python: 100.0, FastAPI: 80.0, PostgreSQL: 60.0
        # 2 Verified challenge submissions -> Experience = 100.0
        evi_py = Evidence(
            profile_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            skill_id=py_skill.id,
            source_type=EvidenceSourceType.CHALLENGE_SUBMISSION,
            source_id=uuid.uuid4(),
            score=100.0,
            evidence_data={},
            status=EvidenceStatus.VERIFIED,
        )
        evi_fastapi = Evidence(
            profile_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            skill_id=fastapi_skill.id,
            source_type=EvidenceSourceType.CHALLENGE_SUBMISSION,
            source_id=uuid.uuid4(),
            score=80.0,
            evidence_data={},
            status=EvidenceStatus.VERIFIED,
        )
        evi_pg = Evidence(
            profile_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            skill_id=pg_skill.id,
            source_type=EvidenceSourceType.ASSESSMENT,
            source_id=uuid.uuid4(),
            score=60.0,
            evidence_data={},
            status=EvidenceStatus.VERIFIED,
        )
        session.add_all([evi_py, evi_fastapi, evi_pg])

        # Learner 2 (44444444-4444-4444-4444-444444444444) has UNVERIFIED evidence for Python (100) -> Coverage = 0
        unverified_evi = Evidence(
            profile_id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
            skill_id=py_skill.id,
            source_type=EvidenceSourceType.CHALLENGE_SUBMISSION,
            source_id=uuid.uuid4(),
            score=100.0,
            evidence_data={},
            status=EvidenceStatus.UNVERIFIED,
        )
        session.add(unverified_evi)
        await session.commit()


@pytest.mark.asyncio
async def test_deterministic_matching_calculation_accuracy(
    async_client: AsyncClient,
    learner_token: str,
    seed_matching_dataset,
):
    """
    Mathematical Proof:
    Skill score:
      (0.5 * 100.0 + 0.3 * 80.0 + 0.2 * 60.0) / (0.5 + 0.3 + 0.2)
      = (50.0 + 24.0 + 12.0) / 1.0 = 86.0
    Evidence score:
      3 verified skills / 3 required skills * 100 = 100.0
    Experience score:
      2 verified challenge submissions = 100.0
    Overall score:
      0.60 * 86.0 + 0.30 * 100.0 + 0.10 * 100.0
      = 51.6 + 30.0 + 10.0 = 91.6%
    """
    opp_id = "88888888-9999-0000-1111-222233334444"

    response = await async_client.post(
        f"/api/v1/matches/opportunities/{opp_id}/calculate",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["skill_score"] == 86.0
    assert data["evidence_score"] == 100.0
    assert data["experience_score"] == 100.0
    assert data["overall_score"] == 91.6

    breakdown = data["breakdown"]
    assert breakdown["matched_skills"] == 3
    assert breakdown["required_skills"] == 3
    assert len(breakdown["skill_details"]) == 3


@pytest.mark.asyncio
async def test_unverified_evidence_produces_zero_coverage(
    async_client: AsyncClient,
    learner_token_2: str,
    seed_matching_dataset,
):
    """Unverified evidence is untrusted and produces 0 coverage."""
    opp_id = "88888888-9999-0000-1111-222233334444"

    response = await async_client.post(
        f"/api/v1/matches/opportunities/{opp_id}/calculate",
        headers={"Authorization": f"Bearer {learner_token_2}"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["skill_score"] == 0.0
    assert data["evidence_score"] == 0.0
    assert data["overall_score"] == 0.0
    assert data["breakdown"]["matched_skills"] == 0


@pytest.mark.asyncio
async def test_self_reported_skills_count_toward_skill_coverage(
    async_client: AsyncClient,
    learner_token_2: str,
    seed_matching_dataset,
):
    """Profile skill claims are compared with job requirements even before verification."""
    opp_id = "88888888-9999-0000-1111-222233334444"
    profile_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    py_skill_id = uuid.UUID("11110000-1111-2222-3333-444455556666")

    async with TestingSessionLocal() as session:
        session.add(
            Evidence(
                profile_id=profile_id,
                skill_id=py_skill_id,
                source_type=EvidenceSourceType.SELF_REPORTED,
                source_id=profile_id,
                score=0.0,
                evidence_data={"self_reported": True, "proficiency": "Intermediate"},
                status=EvidenceStatus.UNVERIFIED,
            )
        )
        await session.commit()

    response = await async_client.post(
        f"/api/v1/matches/opportunities/{opp_id}/calculate",
        headers={"Authorization": f"Bearer {learner_token_2}"},
    )
    assert response.status_code == 200
    data = response.json()

    python_detail = next(
        skill for skill in data["breakdown"]["skill_details"] if skill["skill_name"] == "Python"
    )
    missing = [skill["skill_name"] for skill in data["breakdown"]["skill_details"] if skill["status"] == "missing"]

    assert python_detail["status"] == "weak"
    assert python_detail["coverage"] == 65.0
    assert python_detail["has_verified_evidence"] is False
    assert data["evidence_score"] == 0.0
    assert "FastAPI" in missing
    assert "PostgreSQL" in missing
