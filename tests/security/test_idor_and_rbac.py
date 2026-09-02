import uuid
import pytest
from httpx import AsyncClient
from app.models.role import RoleSkill


@pytest.mark.asyncio
async def test_cross_user_profile_isolation(
    async_client: AsyncClient,
    learner_token: str,
    learner_token_2: str,
):
    """
    Ensures that updating Profile as Learner 1 cannot overwrite Learner 2's profile.
    """
    # Learner 1 updates their profile
    res1 = await async_client.patch(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {learner_token}"},
        json={"full_name": "Learner One", "bio": "Bio for Learner One"},
    )
    assert res1.status_code == 200
    assert res1.json()["id"] == "11111111-1111-1111-1111-111111111111"

    # Learner 2 updates their profile
    res2 = await async_client.patch(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {learner_token_2}"},
        json={"full_name": "Learner Two", "bio": "Bio for Learner Two"},
    )
    assert res2.status_code == 200
    assert res2.json()["id"] == "44444444-4444-4444-4444-444444444444"

    # Fetch Learner 1 profile again and verify it is untampered
    check_res1 = await async_client.get(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert check_res1.json()["full_name"] == "Learner One"
    assert check_res1.json()["bio"] == "Bio for Learner One"


@pytest.mark.asyncio
async def test_cross_organization_data_leakage(
    async_client: AsyncClient,
    employer_token: str,
    learner_token: str,
):
    """
    Ensures unauthorized users cannot fetch member lists of private organizations.
    """
    # Create org by employer
    create_res = await async_client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {employer_token}"},
        json={"name": "Secret Org"},
    )
    org_id = create_res.json()["id"]

    # Attempt to read member roster by unauthorized learner
    leak_attempt = await async_client.get(
        f"/api/v1/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert leak_attempt.status_code == 403
    assert leak_attempt.json()["error"]["code"] == "PERMISSION_DENIED"


def test_role_skill_weight_validation():
    """
    Verifies that importance weights are validated against constraints.
    """
    with pytest.raises(Exception):
        # Weight outside 0.0 - 1.0 range
        from app.schemas.role import RoleSkillItemResponse
        RoleSkillItemResponse(
            id=uuid.uuid4(),
            role_id=uuid.uuid4(),
            skill_id=uuid.uuid4(),
            importance_weight=1.50,  # Invalid
            skill={"id": uuid.uuid4(), "name": "Python", "category": "Dev", "created_at": "2026-08-30T12:00:00Z"},
        )
