import uuid
import pytest
from httpx import AsyncClient
from app.core.constants import OpportunityStatus, OpportunityType, OrgRole, UserRole
from app.models.opportunity import Opportunity
from app.models.opportunity_skill import OpportunitySkill
from app.models.organization import Organization, OrganizationMember
from app.models.profile import Profile
from app.models.skill import Skill
from tests.conftest import TestingSessionLocal, create_mock_jwt


@pytest.fixture
async def seed_opportunity_data():
    async with TestingSessionLocal() as session:
        # Organization
        org = Organization(
            id=uuid.UUID("11111111-aaaa-bbbb-cccc-dddddddddddd"),
            name="TechCorp Labs",
        )
        session.add(org)

        # Employer Profile (Org Admin)
        employer_profile = Profile(
            id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            full_name="Alice Employer",
        )
        session.add(employer_profile)
        await session.flush()

        member = OrganizationMember(
            organization_id=org.id,
            profile_id=employer_profile.id,
            org_role=OrgRole.ADMIN,
        )
        session.add(member)

        # Skills
        skill1 = Skill(
            id=uuid.UUID("33333333-1111-2222-3333-444444444444"),
            name="Python",
            category="Backend",
        )
        skill2 = Skill(
            id=uuid.UUID("44444444-1111-2222-3333-444444444444"),
            name="FastAPI",
            category="Backend",
        )
        session.add_all([skill1, skill2])
        await session.flush()

        # Published Opportunity
        pub_opp = Opportunity(
            id=uuid.UUID("55555555-1111-2222-3333-444444444444"),
            organization_id=org.id,
            title="Senior Backend Engineer",
            description="Build scalable distributed services.",
            opportunity_type=OpportunityType.JOB,
            status=OpportunityStatus.PUBLISHED,
            is_remote=True,
        )
        session.add(pub_opp)
        await session.flush()

        os1 = OpportunitySkill(
            opportunity_id=pub_opp.id,
            skill_id=skill1.id,
            importance_weight=0.6,
        )
        os2 = OpportunitySkill(
            opportunity_id=pub_opp.id,
            skill_id=skill2.id,
            importance_weight=0.4,
        )
        session.add_all([os1, os2])

        # Draft Opportunity
        draft_opp = Opportunity(
            id=uuid.UUID("66666666-1111-2222-3333-444444444444"),
            organization_id=org.id,
            title="Internal AI Apprentice",
            opportunity_type=OpportunityType.APPRENTICESHIP,
            status=OpportunityStatus.DRAFT,
        )
        session.add(draft_opp)
        await session.commit()


@pytest.mark.asyncio
async def test_list_opportunities_shows_published_only_for_learners(
    async_client: AsyncClient,
    seed_opportunity_data,
):
    response = await async_client.get("/api/v1/opportunities")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Senior Backend Engineer"


@pytest.mark.asyncio
async def test_get_opportunity_detail_with_skills(
    async_client: AsyncClient,
    seed_opportunity_data,
):
    opp_id = "55555555-1111-2222-3333-444444444444"
    response = await async_client.get(f"/api/v1/opportunities/{opp_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Senior Backend Engineer"
    assert len(data["skills"]) == 2
    weights = {s["skill_name"]: s["importance_weight"] for s in data["skills"]}
    assert weights["Python"] == 0.6
    assert weights["FastAPI"] == 0.4


@pytest.mark.asyncio
async def test_create_and_publish_opportunity_lifecycle(
    async_client: AsyncClient,
    seed_opportunity_data,
):
    org_id = "11111111-aaaa-bbbb-cccc-dddddddddddd"
    employer_token = create_mock_jwt(
        user_id="22222222-2222-2222-2222-222222222222",
        email="employer@company.com",
        role=UserRole.EMPLOYER,
        org_roles={org_id: OrgRole.ADMIN.value},
    )

    # 1. Employer creates draft opportunity
    create_payload = {
        "organization_id": org_id,
        "title": "Cloud Infrastructure Intern",
        "opportunity_type": "internship",
        "is_remote": True,
        "skills": [
            {
                "skill_id": "33333333-1111-2222-3333-444444444444",
                "importance_weight": 1.0,
            }
        ],
    }
    create_res = await async_client.post(
        "/api/v1/opportunities",
        headers={"Authorization": f"Bearer {employer_token}"},
        json=create_payload,
    )
    assert create_res.status_code == 201
    opp_data = create_res.json()
    opp_id = opp_data["id"]
    assert opp_data["status"] == "draft"

    # 2. Employer publishes opportunity
    pub_res = await async_client.post(
        f"/api/v1/opportunities/{opp_id}/publish",
        headers={"Authorization": f"Bearer {employer_token}"},
    )
    assert pub_res.status_code == 200
    assert pub_res.json()["status"] == "published"

    # 3. Employer closes opportunity
    close_res = await async_client.post(
        f"/api/v1/opportunities/{opp_id}/close",
        headers={"Authorization": f"Bearer {employer_token}"},
    )
    assert close_res.status_code == 200
    assert close_res.json()["status"] == "closed"


@pytest.mark.asyncio
async def test_learner_cannot_create_opportunity(
    async_client: AsyncClient,
    learner_token: str,
    seed_opportunity_data,
):
    payload = {
        "organization_id": "11111111-aaaa-bbbb-cccc-dddddddddddd",
        "title": "Unauthorized Job",
        "opportunity_type": "job",
    }
    response = await async_client.post(
        "/api/v1/opportunities",
        headers={"Authorization": f"Bearer {learner_token}"},
        json=payload,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"
