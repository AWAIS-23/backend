import pytest
from httpx import AsyncClient


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
