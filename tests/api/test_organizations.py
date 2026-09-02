import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_organization_forbidden_for_learner(async_client: AsyncClient, learner_token: str):
    payload = {"name": "Tech Corp", "website_url": "https://techcorp.com"}
    response = await async_client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {learner_token}"},
        json=payload,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_create_organization_success_for_employer(async_client: AsyncClient, employer_token: str):
    payload = {
        "name": "Acme Innovations",
        "website_url": "https://acme.io",
        "logo_url": "https://acme.io/logo.png",
    }
    response = await async_client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {employer_token}"},
        json=payload,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Acme Innovations"
    assert data["website_url"] == "https://acme.io"
    assert "id" in data

    org_id = data["id"]

    # Verify listing user's organizations
    list_res = await async_client.get(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {employer_token}"},
    )
    assert list_res.status_code == 200
    org_list = list_res.json()
    assert len(org_list) >= 1
    assert any(o["id"] == org_id for o in org_list)

    # Verify listing members of the created org
    members_res = await async_client.get(
        f"/api/v1/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {employer_token}"},
    )
    assert members_res.status_code == 200
    members = members_res.json()
    assert len(members) == 1
    assert members[0]["org_role"] == "owner"
    assert members[0]["profile_id"] == "22222222-2222-2222-2222-222222222222"


@pytest.mark.asyncio
async def test_get_organization_details_access_control(
    async_client: AsyncClient,
    employer_token: str,
    learner_token: str,
    admin_token: str,
):
    # Employer creates an organization
    res = await async_client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {employer_token}"},
        json={"name": "Cyberdyne Systems"},
    )
    org_id = res.json()["id"]

    # Employer (owner) can view
    owner_view = await async_client.get(
        f"/api/v1/organizations/{org_id}",
        headers={"Authorization": f"Bearer {employer_token}"},
    )
    assert owner_view.status_code == 200

    # Unrelated learner is forbidden
    learner_view = await async_client.get(
        f"/api/v1/organizations/{org_id}",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert learner_view.status_code == 403

    # Platform admin can view
    admin_view = await async_client.get(
        f"/api/v1/organizations/{org_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_view.status_code == 200
