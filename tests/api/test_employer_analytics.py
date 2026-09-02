"""
Phase 5 — Employer Analytics API Tests
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
from app.models.experience_feedback import ExperienceFeedback
from app.models.opportunity import Opportunity
from app.models.organization import Organization, OrganizationMember
from app.models.profile import Profile
from tests.conftest import TestingSessionLocal, create_mock_jwt


ORG_ID = uuid.UUID("77777777-1111-2222-3333-444444444444")
EMPLOYER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
LEARNER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OPP_ID = uuid.UUID("aaaaaaaa-7777-8888-9999-000000000000")


@pytest.fixture
async def seed_analytics_data():
    async with TestingSessionLocal() as session:
        org = Organization(id=ORG_ID, name="InnoTech Global")
        session.add(org)

        employer_profile = Profile(id=EMPLOYER_ID, full_name="Employer")
        learner_profile = Profile(id=LEARNER_ID, full_name="Learner One")
        session.add_all([employer_profile, learner_profile])
        await session.flush()

        member = OrganizationMember(
            organization_id=ORG_ID,
            profile_id=EMPLOYER_ID,
            org_role=OrgRole.ADMIN,
        )
        session.add(member)

        # Published opportunity
        opp = Opportunity(
            id=OPP_ID,
            organization_id=ORG_ID,
            title="Backend Intern",
            opportunity_type=OpportunityType.INTERNSHIP,
            status=OpportunityStatus.PUBLISHED,
            deadline=datetime.now(timezone.utc) + timedelta(days=30),
        )
        session.add(opp)
        await session.flush()

        # Accepted application
        app = Application(
            opportunity_id=OPP_ID,
            profile_id=LEARNER_ID,
            status=ApplicationStatus.ACCEPTED,
        )
        session.add(app)
        await session.flush()

        # Completed experience
        exp = Experience(
            profile_id=LEARNER_ID,
            organization_id=ORG_ID,
            opportunity_id=OPP_ID,
            application_id=app.id,
            title="Backend Intern Experience",
            experience_type=ExperienceType.INTERNSHIP,
            started_at=datetime.now(timezone.utc) - timedelta(days=60),
            ended_at=datetime.now(timezone.utc),
            status=ExperienceStatus.COMPLETED,
            verification_status=VerificationStatus.VERIFIED,
        )
        session.add(exp)
        await session.flush()

        # Feedback on that experience
        fb = ExperienceFeedback(
            experience_id=exp.id,
            profile_id=LEARNER_ID,
            organization_id=ORG_ID,
            reviewer_id=EMPLOYER_ID,
            overall_rating=4,
            strengths="Solid engineer.",
        )
        session.add(fb)
        await session.commit()


def _employer_jwt():
    return create_mock_jwt(
        user_id=str(EMPLOYER_ID),
        email="employer@company.com",
        role=UserRole.EMPLOYER,
        org_roles={str(ORG_ID): OrgRole.ADMIN.value},
    )


def _learner_jwt():
    return create_mock_jwt(
        user_id=str(LEARNER_ID),
        email="learner@risingskills.com",
        role=UserRole.LEARNER,
    )


@pytest.mark.asyncio
async def test_employer_gets_organization_analytics(
    async_client: AsyncClient, seed_analytics_data
):
    res = await async_client.get(
        f"/api/v1/analytics/organizations/{ORG_ID}",
        headers={"Authorization": f"Bearer {_employer_jwt()}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["organization_id"] == str(ORG_ID)
    assert data["total_opportunities"] >= 1
    assert data["published_opportunities"] >= 1
    assert data["total_applications"] >= 1
    assert data["accepted_applications"] >= 1
    assert data["completed_experiences"] >= 1
    assert data["average_feedback_rating"] > 0


@pytest.mark.asyncio
async def test_learner_cannot_access_organization_analytics(
    async_client: AsyncClient, seed_analytics_data
):
    res = await async_client.get(
        f"/api/v1/analytics/organizations/{ORG_ID}",
        headers={"Authorization": f"Bearer {_learner_jwt()}"},
    )
    assert res.status_code == 403
