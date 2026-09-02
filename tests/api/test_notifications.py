"""
Phase 5 — Notifications API Tests
"""
import uuid
import pytest
from httpx import AsyncClient
from app.core.constants import (
    ApplicationStatus,
    NotificationType,
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
from datetime import datetime, timedelta, timezone

ORG_ID = uuid.UUID("77777777-1111-2222-3333-444444444444")
EMPLOYER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
LEARNER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OPP_ID = uuid.UUID("aaaaaaaa-7777-8888-9999-000000000000")
APP_ID = uuid.UUID("cccccccc-1111-2222-3333-444444444444")


@pytest.fixture
async def seed_notification_data():
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

        opp = Opportunity(
            id=OPP_ID,
            organization_id=ORG_ID,
            title="Backend Engineer Intern",
            opportunity_type=OpportunityType.INTERNSHIP,
            status=OpportunityStatus.PUBLISHED,
            deadline=datetime.now(timezone.utc) + timedelta(days=30),
        )
        session.add(opp)
        await session.flush()

        app = Application(
            id=APP_ID,
            opportunity_id=OPP_ID,
            profile_id=LEARNER_ID,
            status=ApplicationStatus.ACCEPTED,
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


@pytest.mark.asyncio
async def test_notifications_created_on_experience_activation(
    async_client: AsyncClient, seed_notification_data
):
    """Creating an experience from accepted app should create a notification for the learner."""
    await async_client.post(
        f"/api/v1/experiences/from-application/{APP_ID}",
        headers={"Authorization": f"Bearer {_employer_jwt()}"},
    )

    # Learner checks notifications
    res = await async_client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {_learner_jwt()}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert any(n["notification_type"] == NotificationType.EXPERIENCE_CREATED for n in data["items"])


@pytest.mark.asyncio
async def test_mark_notification_as_read(
    async_client: AsyncClient, seed_notification_data
):
    # Trigger notification
    await async_client.post(
        f"/api/v1/experiences/from-application/{APP_ID}",
        headers={"Authorization": f"Bearer {_employer_jwt()}"},
    )

    list_res = await async_client.get(
        "/api/v1/notifications?unread_only=true",
        headers={"Authorization": f"Bearer {_learner_jwt()}"},
    )
    notif_id = list_res.json()["items"][0]["id"]

    # Mark as read
    read_res = await async_client.patch(
        f"/api/v1/notifications/{notif_id}/read",
        headers={"Authorization": f"Bearer {_learner_jwt()}"},
    )
    assert read_res.status_code == 200
    assert read_res.json()["is_read"] is True


@pytest.mark.asyncio
async def test_mark_all_notifications_as_read(
    async_client: AsyncClient, seed_notification_data
):
    # Create multiple notifications
    await async_client.post(
        f"/api/v1/experiences/from-application/{APP_ID}",
        headers={"Authorization": f"Bearer {_employer_jwt()}"},
    )

    res = await async_client.post(
        "/api/v1/notifications/read-all",
        headers={"Authorization": f"Bearer {_learner_jwt()}"},
    )
    assert res.status_code == 200
    assert res.json()["marked_read"] >= 1

    # Verify all are read
    list_res = await async_client.get(
        "/api/v1/notifications?unread_only=true",
        headers={"Authorization": f"Bearer {_learner_jwt()}"},
    )
    assert list_res.json()["total"] == 0
