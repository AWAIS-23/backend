import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from app.core.constants import OpportunityStatus, OpportunityType, OrgRole, UserRole
from app.models.opportunity import Opportunity
from app.models.organization import Organization, OrganizationMember
from app.models.profile import Profile
from tests.conftest import TestingSessionLocal, create_mock_jwt


@pytest.fixture
async def seed_application_data():
    async with TestingSessionLocal() as session:
        org = Organization(
            id=uuid.UUID("77777777-1111-2222-3333-444444444444"),
            name="InnoTech Global",
        )
        session.add(org)

        employer_profile = Profile(
            id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            full_name="Employer Reviewer",
        )
        session.add(employer_profile)
        await session.flush()

        member = OrganizationMember(
            organization_id=org.id,
            profile_id=employer_profile.id,
            org_role=OrgRole.RECRUITER,
        )
        session.add(member)

        # Open Opportunity
        open_opp = Opportunity(
            id=uuid.UUID("aaaaaaaa-7777-8888-9999-000000000000"),
            organization_id=org.id,
            title="Full Stack Software Engineer",
            opportunity_type=OpportunityType.JOB,
            status=OpportunityStatus.PUBLISHED,
            deadline=datetime.now(timezone.utc) + timedelta(days=14),
        )

        # Closed Opportunity
        closed_opp = Opportunity(
            id=uuid.UUID("bbbbbbbb-7777-8888-9999-000000000000"),
            organization_id=org.id,
            title="Archived Opportunity",
            opportunity_type=OpportunityType.JOB,
            status=OpportunityStatus.CLOSED,
        )
        session.add_all([open_opp, closed_opp])
        await session.commit()


@pytest.mark.asyncio
async def test_full_application_lifecycle_and_review(
    async_client: AsyncClient,
    learner_token: str,
    seed_application_data,
):
    opp_id = "aaaaaaaa-7777-8888-9999-000000000000"
    org_id = "77777777-1111-2222-3333-444444444444"
    employer_token = create_mock_jwt(
        user_id="22222222-2222-2222-2222-222222222222",
        email="employer@company.com",
        role=UserRole.EMPLOYER,
        org_roles={org_id: OrgRole.RECRUITER.value},
    )

    # 1. Learner applies
    apply_res = await async_client.post(
        f"/api/v1/opportunities/{opp_id}/apply",
        headers={"Authorization": f"Bearer {learner_token}"},
        json={"cover_note": "Excited to apply for the Full Stack role!"},
    )
    assert apply_res.status_code == 201
    app_data = apply_res.json()
    app_id = app_data["id"]
    assert app_data["status"] == "submitted"

    # 2. Duplicate application to same opportunity rejected with 409
    dup_res = await async_client.post(
        f"/api/v1/opportunities/{opp_id}/apply",
        headers={"Authorization": f"Bearer {learner_token}"},
        json={"cover_note": "Trying to apply again."},
    )
    assert dup_res.status_code == 409
    assert dup_res.json()["error"]["code"] == "DUPLICATE_APPLICATION"

    # 3. Employer reviews and shortlists candidate
    review_res = await async_client.patch(
        f"/api/v1/applications/{app_id}/status",
        headers={"Authorization": f"Bearer {employer_token}"},
        json={"status": "shortlisted"},
    )
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "shortlisted"

    # 4. Employer accepts candidate
    accept_res = await async_client.patch(
        f"/api/v1/applications/{app_id}/status",
        headers={"Authorization": f"Bearer {employer_token}"},
        json={"status": "accepted"},
    )
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == "accepted"


@pytest.mark.asyncio
async def test_learner_withdraws_application(
    async_client: AsyncClient,
    learner_token: str,
    seed_application_data,
):
    opp_id = "aaaaaaaa-7777-8888-9999-000000000000"

    # Apply
    apply_res = await async_client.post(
        f"/api/v1/opportunities/{opp_id}/apply",
        headers={"Authorization": f"Bearer {learner_token}"},
        json={"cover_note": "Submitting application."},
    )
    app_id = apply_res.json()["id"]

    # Withdraw
    withdraw_res = await async_client.patch(
        f"/api/v1/applications/{app_id}/withdraw",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert withdraw_res.status_code == 200
    assert withdraw_res.json()["status"] == "withdrawn"


@pytest.mark.asyncio
async def test_apply_to_closed_opportunity_rejected(
    async_client: AsyncClient,
    learner_token: str,
    seed_application_data,
):
    closed_id = "bbbbbbbb-7777-8888-9999-000000000000"
    response = await async_client.post(
        f"/api/v1/opportunities/{closed_id}/apply",
        headers={"Authorization": f"Bearer {learner_token}"},
        json={"cover_note": "Applying to closed opportunity."},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "OPPORTUNITY_NOT_PUBLISHED"
