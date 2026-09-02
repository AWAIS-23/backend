import uuid
import pytest
from httpx import AsyncClient
from app.core.constants import (
    ApplicationStatus,
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


@pytest.fixture
async def seed_phase4_security_data():
    async with TestingSessionLocal() as session:
        # Organization A
        org_a = Organization(
            id=uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001"),
            name="Org Alpha",
        )
        # Organization B
        org_b = Organization(
            id=uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002"),
            name="Org Beta",
        )
        session.add_all([org_a, org_b])

        # Opportunity in Org A
        opp_a = Opportunity(
            id=uuid.UUID("aaaaaaaa-1111-1111-1111-111111111111"),
            organization_id=org_a.id,
            title="Org A Backend Engineer",
            opportunity_type=OpportunityType.JOB,
            status=OpportunityStatus.PUBLISHED,
        )
        session.add(opp_a)
        await session.flush()

        # Learner 1 application to Org A opportunity
        app1 = Application(
            id=uuid.UUID("cccccccc-1111-1111-1111-111111111111"),
            opportunity_id=opp_a.id,
            profile_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            status=ApplicationStatus.SUBMITTED,
            cover_note="Learner 1 application.",
        )
        session.add(app1)
        await session.commit()


@pytest.mark.asyncio
async def test_cross_learner_application_tampering_blocked(
    async_client: AsyncClient,
    learner_token_2: str,
    seed_phase4_security_data,
):
    """Learner 2 cannot withdraw or view Learner 1's application."""
    app1_id = "cccccccc-1111-1111-1111-111111111111"

    # Learner 2 tries to withdraw Learner 1's application
    withdraw_res = await async_client.patch(
        f"/api/v1/applications/{app1_id}/withdraw",
        headers={"Authorization": f"Bearer {learner_token_2}"},
    )
    assert withdraw_res.status_code == 403
    assert withdraw_res.json()["error"]["code"] == "PERMISSION_DENIED"

    # Learner 2 tries to view Learner 1's application
    get_res = await async_client.get(
        f"/api/v1/applications/{app1_id}",
        headers={"Authorization": f"Bearer {learner_token_2}"},
    )
    assert get_res.status_code == 403
    assert get_res.json()["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_cross_organization_employer_isolation(
    async_client: AsyncClient,
    seed_phase4_security_data,
):
    """Employer from Org Beta cannot review or update applications for Org Alpha."""
    employer_b_token = create_mock_jwt(
        user_id="99999999-9999-9999-9999-999999999999",
        email="employer_b@orgbeta.com",
        role=UserRole.EMPLOYER,
        org_roles={"bbbbbbbb-0000-0000-0000-000000000002": OrgRole.ADMIN.value},
    )
    app1_id = "cccccccc-1111-1111-1111-111111111111"

    # Employer B tries to change status of Org Alpha's application
    res = await async_client.patch(
        f"/api/v1/applications/{app1_id}/status",
        headers={"Authorization": f"Bearer {employer_b_token}"},
        json={"status": "accepted"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "PERMISSION_DENIED"
