import pytest
from httpx import AsyncClient

from tests.conftest import create_mock_jwt


@pytest.mark.asyncio
async def test_get_profile_unauthenticated(async_client: AsyncClient):
    response = await async_client.get("/api/v1/profiles/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


@pytest.mark.asyncio
async def test_get_profile_authenticated_auto_initializes(async_client: AsyncClient, learner_token: str):
    response = await async_client.get(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "11111111-1111-1111-1111-111111111111"
    assert data["role"] == "learner"


@pytest.mark.asyncio
async def test_get_profile_seeds_full_name_and_avatar_from_jwt(async_client: AsyncClient):
    """On first login, full_name/avatar_url from Supabase user_metadata should be seeded."""
    token = create_mock_jwt(
        user_id="55555555-5555-5555-5555-555555555555",
        email="newuser@risingskills.com",
        full_name="Nida Karamat",
        avatar_url="https://example.com/avatar.png",
    )
    response = await async_client.get(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "55555555-5555-5555-5555-555555555555"
    assert data["full_name"] == "Nida Karamat"
    assert data["avatar_url"] == "https://example.com/avatar.png"


@pytest.mark.asyncio
async def test_get_profile_does_not_overwrite_existing_full_name(async_client: AsyncClient):
    """Seed values must not overwrite a profile that already has full_name set."""
    token = create_mock_jwt(
        user_id="66666666-6666-6666-6666-666666666666",
        email="existing@risingskills.com",
        full_name="JWT Seed Name",
    )
    # First call seeds the profile.
    r1 = await async_client.get(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 200
    assert r1.json()["full_name"] == "JWT Seed Name"

    # Update the profile to a different name.
    r2 = await async_client.patch(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"full_name": "Updated Name"},
    )
    assert r2.status_code == 200
    assert r2.json()["full_name"] == "Updated Name"

    # Second GET must NOT revert to the JWT seed value.
    r3 = await async_client.get(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r3.status_code == 200
    assert r3.json()["full_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_get_profile_backfills_null_full_name_on_existing_profile(async_client: AsyncClient):
    """An existing profile with null full_name should be backfilled from JWT on next login.

    This covers users who signed up before the seed-on-create fix was deployed.
    """
    user_id = "77777777-7777-7777-7777-777777777777"
    # Step 1: create the profile WITHOUT a full_name (simulates legacy signup).
    legacy_token = create_mock_jwt(
        user_id=user_id,
        email="legacy@risingskills.com",
        # no full_name / avatar_url in this token
    )
    r1 = await async_client.get(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {legacy_token}"},
    )
    assert r1.status_code == 200
    assert r1.json()["full_name"] is None
    assert r1.json()["avatar_url"] is None

    # Step 2: user logs in again with a token that now carries full_name
    # (e.g. Supabase user_metadata was populated).
    seeded_token = create_mock_jwt(
        user_id=user_id,
        email="legacy@risingskills.com",
        full_name="Nida Karamat",
        avatar_url="https://example.com/avatar.png",
    )
    r2 = await async_client.get(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {seeded_token}"},
    )
    assert r2.status_code == 200
    data = r2.json()
    # Null fields should now be backfilled from the JWT.
    assert data["full_name"] == "Nida Karamat"
    assert data["avatar_url"] == "https://example.com/avatar.png"


@pytest.mark.asyncio
async def test_update_profile_success(async_client: AsyncClient, learner_token: str):
    payload = {
        "full_name": "Alice Developer",
        "bio": "Aspiring full-stack engineer and open source enthusiast.",
        "avatar_url": "https://example.com/avatar.png",
    }
    response = await async_client.patch(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {learner_token}"},
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Alice Developer"
    assert data["bio"] == "Aspiring full-stack engineer and open source enthusiast."
    assert data["avatar_url"] == "https://example.com/avatar.png"


@pytest.mark.asyncio
async def test_update_profile_cannot_escalate_role(async_client: AsyncClient, learner_token: str):
    # Attempting to send role in payload
    payload = {
        "full_name": "Alice Developer",
        "role": "admin",  # Attacker trying to escalate
    }
    response = await async_client.patch(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {learner_token}"},
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    # Role remains learner
    assert data["role"] == "learner"
