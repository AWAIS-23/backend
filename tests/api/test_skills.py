import uuid
import pytest
from httpx import AsyncClient
from app.models.skill import Skill
from tests.conftest import TestingSessionLocal


@pytest.fixture
async def seed_skills():
    async with TestingSessionLocal() as session:
        parent_be = Skill(
            id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            name="Backend Development",
            category="Software Engineering",
            parent_skill_id=None,
        )
        child_py = Skill(
            id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            name="Python",
            category="Programming Language",
            parent_skill_id=parent_be.id,
        )
        child_fastapi = Skill(
            id=uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
            name="FastAPI",
            category="Web Framework",
            parent_skill_id=parent_be.id,
        )
        session.add_all([parent_be, child_py, child_fastapi])
        await session.commit()


@pytest.mark.asyncio
async def test_list_skills_pagination_and_search(async_client: AsyncClient, seed_skills):
    # List all skills
    response = await async_client.get("/api/v1/skills")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3
    assert len(data["items"]) >= 3

    # Search filter
    search_res = await async_client.get("/api/v1/skills?search=python")
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total"] == 1
    assert search_data["items"][0]["name"] == "Python"

    # Category filter
    cat_res = await async_client.get("/api/v1/skills?category=Web Framework")
    assert cat_res.status_code == 200
    cat_data = cat_res.json()
    assert cat_data["total"] == 1
    assert cat_data["items"][0]["name"] == "FastAPI"


@pytest.mark.asyncio
async def test_get_skill_by_id(async_client: AsyncClient, seed_skills):
    skill_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    response = await async_client.get(f"/api/v1/skills/{skill_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Backend Development"
    assert data["id"] == skill_id


@pytest.mark.asyncio
async def test_get_skill_children(async_client: AsyncClient, seed_skills):
    parent_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    response = await async_client.get(f"/api/v1/skills/{parent_id}/children")
    assert response.status_code == 200
    children = response.json()
    assert len(children) == 2
    names = [c["name"] for c in children]
    assert "Python" in names
    assert "FastAPI" in names


@pytest.mark.asyncio
async def test_get_skill_not_found(async_client: AsyncClient):
    random_id = uuid.uuid4()
    response = await async_client.get(f"/api/v1/skills/{random_id}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
