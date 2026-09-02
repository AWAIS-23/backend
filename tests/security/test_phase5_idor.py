"""
Phase 5 — IDOR & Organization Isolation Security Tests
for Experience, Feedback, and Analytics
"""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from app.core.constants import (
    ApplicationStatus,
    ExperienceStatus,
    ExperienceType,
    OpportunityStatus,
    OpportunityType,
    OrgRole,
    UserRole,
    VerificationStatus,
)
from app.models.application import Application
from app.models.experience import Experience
from app.models.opportunity import Opportunity
from app.models.organization import Organization, OrganizationMember
from app.models.profile import Profile
from tests.conftest import TestingSessionLocal, create_mock_jwt


ORG_A_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
ORG_B_ID = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")
EMPLOYER_A_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
EMPLOYER_B_ID = uuid.UUID("99999999-9999-9999-9999-999999999999")
LEARNER_1_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
LEARNER_2_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
OPP_A_ID = uuid.UUID("aaaaaaaa-1111-1111-1111-111111111111")
APP_A_ID = uuid.UUID("cccccccc-1111-1111-1111-111111111111")
EXP_A_ID = uuid.UUID("eeeeeeee-1111-1111-1111-111111111111")


@pytest.fixture
async def seed_phase5_security_data():
    async with TestingSessionLocal() as session:
        org_a = Organization(id=ORG_A_ID, name="Org Alpha")
        org_b = Organization(id=ORG_B_ID, name="Org Beta")
        session.add_all([org_a, org_b])

        emp_a = Profile(id=EMPLOYER_A_ID, full_name="Employer A")
        emp_b = Profile(id=EMPLOYER_B_ID, full_name="Employer B")
        learner_1 = Profile(id=LEARNER_1_ID, full_name="Learner One")
        learner_2 = Profile(id=LEARNER_2_ID, full_name="Learner Two")
        session.add_all([emp_a, emp_b, learner_1, learner_2])
        await session.flush()

        mem_a = OrganizationMember(
            organization_id=ORG_A_ID,
            profile_id=EMPLOYER_A_ID,
            org_role=OrgRole.ADMIN,
        )
        mem_b = OrganizationMember(
            organization_id=ORG_B_ID,
            profile_id=EMPLOYER_B_ID,
            org_role=OrgRole.ADMIN,
        )
        session.add_all([mem_a, mem_b])

        opp_a = Opportunity(
            id=OPP_A_ID,
            organization_id=ORG_A_ID,
            title="Org A Job",
            opportunity_type=OpportunityType.JOB,
            status=OpportunityStatus.PUBLISHED,
        )
        session.add(opp_a)
        await session.flush()

        app_a = Application(
            id=APP_A_ID,
            opportunity_id=OPP_A_ID,
            profile_id=LEARNER_1_ID,
            status=ApplicationStatus.ACCEPTED,
        )
        session.add(app_a)
        await session.flush()

        # Active experience belonging to Learner 1, Org Alpha
        exp_a = Experience(
            id=EXP_A_ID,
            profile_id=LEARNER_1_ID,
            organization_id=ORG_A_ID,
            opportunity_id=OPP_A_ID,
            application_id=APP_A_ID,
            title="Org A Experience",
            experience_type=ExperienceType.INTERNSHIP,
            started_at=datetime.now(timezone.utc) - timedelta(days=30),
            status=ExperienceStatus.ACTIVE,
            verification_status=VerificationStatus.VERIFIED,
        )
        session.add(exp_a)
        await session.commit()


def _employer_a_jwt():
    return create_mock_jwt(
        user_id=str(EMPLOYER_A_ID),
        email="employer_a@orgalpha.com",
        role=UserRole.EMPLOYER,
        org_roles={str(ORG_A_ID): OrgRole.ADMIN.value},
    )


def _employer_b_jwt():
    return create_mock_jwt(
        user_id=str(EMPLOYER_B_ID),
        email="employer_b@orgbeta.com",
        role=UserRole.EMPLOYER,
        org_roles={str(ORG_B_ID): OrgRole.ADMIN.value},
    )


def _learner_1_jwt():
    return create_mock_jwt(
        user_id=str(LEARNER_1_ID),
        email="learner1@risingskills.com",
        role=UserRole.LEARNER,
    )


def _learner_2_jwt():
    return create_mock_jwt(
        user_id=str(LEARNER_2_ID),
        email="learner2@risingskills.com",
        role=UserRole.LEARNER,
    )


# ──────────────────────────────────────────────
# 1. Cross-Org Employer Cannot View Experiences of Another Org
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_cross_org_employer_cannot_view_experience(
    async_client: AsyncClient, seed_phase5_security_data
):
    res = await async_client.get(
        f"/api/v1/experiences/{EXP_A_ID}",
        headers={"Authorization": f"Bearer {_employer_b_jwt()}"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "PERMISSION_DENIED"


# ──────────────────────────────────────────────
# 2. Cross-Org Employer Cannot Submit Feedback for Another Org's Experience
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_cross_org_employer_cannot_submit_feedback(
    async_client: AsyncClient, seed_phase5_security_data
):
    res = await async_client.post(
        f"/api/v1/experiences/{EXP_A_ID}/feedback",
        headers={"Authorization": f"Bearer {_employer_b_jwt()}"},
        json={"overall_rating": 5},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "PERMISSION_DENIED"


# ──────────────────────────────────────────────
# 3. Cross-Learner Cannot View Another Learner's Experience
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_cross_learner_cannot_view_experience(
    async_client: AsyncClient, seed_phase5_security_data
):
    res = await async_client.get(
        f"/api/v1/experiences/{EXP_A_ID}",
        headers={"Authorization": f"Bearer {_learner_2_jwt()}"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "PERMISSION_DENIED"


# ──────────────────────────────────────────────
# 4. Learner Cannot Submit Employer Feedback
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_learner_cannot_submit_feedback(
    async_client: AsyncClient, seed_phase5_security_data
):
    res = await async_client.post(
        f"/api/v1/experiences/{EXP_A_ID}/feedback",
        headers={"Authorization": f"Bearer {_learner_1_jwt()}"},
        json={"overall_rating": 5},
    )
    assert res.status_code == 403


# ──────────────────────────────────────────────
# 5. Cross-Org Analytics Isolation
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_cross_org_analytics_blocked(
    async_client: AsyncClient, seed_phase5_security_data
):
    """Employer from Org B cannot access analytics for Org A."""
    res = await async_client.get(
        f"/api/v1/analytics/organizations/{ORG_A_ID}",
        headers={"Authorization": f"Bearer {_employer_b_jwt()}"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "PERMISSION_DENIED"
