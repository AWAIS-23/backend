"""
Phase 5 — Experience Lifecycle, Application→Experience Transition,
Employer Feedback, and State Transition Tests
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
)
from app.models.application import Application
from app.models.opportunity import Opportunity
from app.models.organization import Organization, OrganizationMember
from app.models.profile import Profile
from tests.conftest import TestingSessionLocal, create_mock_jwt


ORG_ID = uuid.UUID("77777777-1111-2222-3333-444444444444")
EMPLOYER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
LEARNER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
LEARNER_2_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
OPP_ID = uuid.UUID("aaaaaaaa-7777-8888-9999-000000000000")
APP_ID = uuid.UUID("cccccccc-1111-2222-3333-444444444444")


@pytest.fixture
async def seed_experience_data():
    async with TestingSessionLocal() as session:
        org = Organization(id=ORG_ID, name="InnoTech Global")
        session.add(org)

        employer_profile = Profile(id=EMPLOYER_ID, full_name="Employer Reviewer")
        learner_profile = Profile(id=LEARNER_ID, full_name="Learner One")
        session.add_all([employer_profile, learner_profile])
        await session.flush()

        member = OrganizationMember(
            organization_id=ORG_ID,
            profile_id=EMPLOYER_ID,
            org_role=OrgRole.ADMIN,
        )
        session.add(member)

        opp = Opportunity(
            id=OPP_ID,
            organization_id=ORG_ID,
            title="Backend Engineer Intern",
            description="Build APIs for Rising Skills.",
            opportunity_type=OpportunityType.INTERNSHIP,
            status=OpportunityStatus.PUBLISHED,
            deadline=datetime.now(timezone.utc) + timedelta(days=30),
        )
        session.add(opp)
        await session.flush()

        # Accepted application — gate for experience creation
        app = Application(
            id=APP_ID,
            opportunity_id=OPP_ID,
            profile_id=LEARNER_ID,
            status=ApplicationStatus.ACCEPTED,
            cover_note="I'm excited to join!",
        )
        session.add(app)
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


def _learner_2_jwt():
    return create_mock_jwt(
        user_id=str(LEARNER_2_ID),
        email="learner2@risingskills.com",
        role=UserRole.LEARNER,
    )


# ──────────────────────────────────────────────
# 1. Create Experience from Accepted Application
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_create_experience_from_accepted_application(
    async_client: AsyncClient, seed_experience_data
):
    res = await async_client.post(
        f"/api/v1/experiences/from-application/{APP_ID}",
        headers={"Authorization": f"Bearer {_employer_jwt()}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == ExperienceStatus.ACTIVE
    assert data["profile_id"] == str(LEARNER_ID)
    assert data["organization_id"] == str(ORG_ID)
    assert data["opportunity_id"] == str(OPP_ID)
    assert data["title"] == "Backend Engineer Intern"


# ──────────────────────────────────────────────
# 2. Reject Experience Creation from Non-Accepted Application
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_reject_experience_from_non_accepted_application(
    async_client: AsyncClient,
):
    # Seed a submitted (not accepted) application
    submitted_app_id = uuid.UUID("dddddddd-1111-2222-3333-444444444444")
    async with TestingSessionLocal() as session:
        org = Organization(id=ORG_ID, name="InnoTech Global")
        session.add(org)
        employer_profile = Profile(id=EMPLOYER_ID, full_name="Employer Reviewer")
        learner_profile = Profile(id=LEARNER_ID, full_name="Learner One")
        session.add_all([employer_profile, learner_profile])
        await session.flush()
        member = OrganizationMember(
            organization_id=ORG_ID,
            profile_id=EMPLOYER_ID,
            org_role=OrgRole.ADMIN,
        )
        session.add(member)
        opp = Opportunity(
            id=OPP_ID,
            organization_id=ORG_ID,
            title="Backend Engineer Intern",
            opportunity_type=OpportunityType.INTERNSHIP,
            status=OpportunityStatus.PUBLISHED,
        )
        session.add(opp)
        await session.flush()
        app = Application(
            id=submitted_app_id,
            opportunity_id=OPP_ID,
            profile_id=LEARNER_ID,
            status=ApplicationStatus.SUBMITTED,
        )
        session.add(app)
        await session.commit()

    res = await async_client.post(
        f"/api/v1/experiences/from-application/{submitted_app_id}",
        headers={"Authorization": f"Bearer {_employer_jwt()}"},
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "APPLICATION_NOT_ACCEPTED"


# ──────────────────────────────────────────────
# 3. Complete Experience Lifecycle
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_complete_experience_lifecycle(
    async_client: AsyncClient, seed_experience_data
):
    # Create experience
    create_res = await async_client.post(
        f"/api/v1/experiences/from-application/{APP_ID}",
        headers={"Authorization": f"Bearer {_employer_jwt()}"},
    )
    assert create_res.status_code == 201
    exp_id = create_res.json()["id"]

    # Complete it
    complete_res = await async_client.post(
        f"/api/v1/experiences/{exp_id}/complete",
        headers={"Authorization": f"Bearer {_employer_jwt()}"},
    )
    assert complete_res.status_code == 200
    assert complete_res.json()["status"] == ExperienceStatus.COMPLETED
    assert complete_res.json()["ended_at"] is not None


# ──────────────────────────────────────────────
# 4. Double-Complete Raises Error
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_double_complete_experience_raises_error(
    async_client: AsyncClient, seed_experience_data
):
    create_res = await async_client.post(
        f"/api/v1/experiences/from-application/{APP_ID}",
        headers={"Authorization": f"Bearer {_employer_jwt()}"},
    )
    exp_id = create_res.json()["id"]

    # First complete
    await async_client.post(
        f"/api/v1/experiences/{exp_id}/complete",
        headers={"Authorization": f"Bearer {_employer_jwt()}"},
    )

    # Second complete
    res = await async_client.post(
        f"/api/v1/experiences/{exp_id}/complete",
        headers={"Authorization": f"Bearer {_employer_jwt()}"},
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "EXPERIENCE_ALREADY_COMPLETED"


# ──────────────────────────────────────────────
# 5. Learner Can View Own Experiences
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_learner_lists_own_experiences(
    async_client: AsyncClient, seed_experience_data
):
    # Employer creates experience for learner
    await async_client.post(
        f"/api/v1/experiences/from-application/{APP_ID}",
        headers={"Authorization": f"Bearer {_employer_jwt()}"},
    )

    # Learner lists own experiences
    res = await async_client.get(
        "/api/v1/experiences/me",
        headers={"Authorization": f"Bearer {_learner_jwt()}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert data["items"][0]["profile_id"] == str(LEARNER_ID)


# ──────────────────────────────────────────────
# 6. Employer Submits Feedback on Experience
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_employer_submits_feedback(
    async_client: AsyncClient, seed_experience_data
):
    create_res = await async_client.post(
        f"/api/v1/experiences/from-application/{APP_ID}",
        headers={"Authorization": f"Bearer {_employer_jwt()}"},
    )
    exp_id = create_res.json()["id"]

    feedback_payload = {
        "overall_rating": 4,
        "strengths": "Strong problem-solving skills.",
        "areas_for_improvement": "Communication could improve.",
        "communication_rating": 3,
        "technical_rating": 5,
        "problem_solving_rating": 4,
        "teamwork_rating": 4,
        "professionalism_rating": 5,
        "recommendation": "Would hire again.",
    }
    fb_res = await async_client.post(
        f"/api/v1/experiences/{exp_id}/feedback",
        headers={"Authorization": f"Bearer {_employer_jwt()}"},
        json=feedback_payload,
    )
    assert fb_res.status_code == 201
    fb_data = fb_res.json()
    assert fb_data["overall_rating"] == 4
    assert fb_data["reviewer_id"] == str(EMPLOYER_ID)
    assert fb_data["profile_id"] == str(LEARNER_ID)


# ──────────────────────────────────────────────
# 7. Duplicate Feedback Rejected
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_duplicate_feedback_rejected(
    async_client: AsyncClient, seed_experience_data
):
    create_res = await async_client.post(
        f"/api/v1/experiences/from-application/{APP_ID}",
        headers={"Authorization": f"Bearer {_employer_jwt()}"},
    )
    exp_id = create_res.json()["id"]

    payload = {"overall_rating": 4}

    # First feedback
    res1 = await async_client.post(
        f"/api/v1/experiences/{exp_id}/feedback",
        headers={"Authorization": f"Bearer {_employer_jwt()}"},
        json=payload,
    )
    assert res1.status_code == 201

    # Duplicate attempt
    res2 = await async_client.post(
        f"/api/v1/experiences/{exp_id}/feedback",
        headers={"Authorization": f"Bearer {_employer_jwt()}"},
        json=payload,
    )
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "DUPLICATE_FEEDBACK"


# ──────────────────────────────────────────────
# 8. List Feedback for Experience
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_list_feedback_for_experience(
    async_client: AsyncClient, seed_experience_data
):
    create_res = await async_client.post(
        f"/api/v1/experiences/from-application/{APP_ID}",
        headers={"Authorization": f"Bearer {_employer_jwt()}"},
    )
    exp_id = create_res.json()["id"]

    # Submit feedback
    await async_client.post(
        f"/api/v1/experiences/{exp_id}/feedback",
        headers={"Authorization": f"Bearer {_employer_jwt()}"},
        json={"overall_rating": 5, "strengths": "Outstanding."},
    )

    # Learner views feedback on their experience
    res = await async_client.get(
        f"/api/v1/experiences/{exp_id}/feedback",
        headers={"Authorization": f"Bearer {_learner_jwt()}"},
    )
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 1
    assert items[0]["overall_rating"] == 5


# ──────────────────────────────────────────────
# 9. Feedback Rating Validation (Out of Range)
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_feedback_rating_validation(
    async_client: AsyncClient, seed_experience_data
):
    create_res = await async_client.post(
        f"/api/v1/experiences/from-application/{APP_ID}",
        headers={"Authorization": f"Bearer {_employer_jwt()}"},
    )
    exp_id = create_res.json()["id"]

    # Rating out of range (6)
    res = await async_client.post(
        f"/api/v1/experiences/{exp_id}/feedback",
        headers={"Authorization": f"Bearer {_employer_jwt()}"},
        json={"overall_rating": 6},
    )
    assert res.status_code == 422
