import uuid
import pytest
from httpx import AsyncClient
from app.models.role import Role, RoleSkill
from app.models.skill import Skill
from tests.conftest import TestingSessionLocal


@pytest.fixture
async def seed_roles_and_skills():
    async with TestingSessionLocal() as session:
        # Create a skill
        skill_python = Skill(
            id=uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
            name="Python Programming",
            category="Programming",
        )
        skill_sql = Skill(
            id=uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
            name="PostgreSQL",
            category="Database",
        )
        session.add_all([skill_python, skill_sql])
        await session.flush()

        # Create a role
        role_be = Role(
            id=uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
            title="Backend Engineer",
            description="Designs and builds scalable server-side systems and APIs.",
        )
        session.add(role_be)
        await session.flush()

        # Map role to skills with weights
        rs1 = RoleSkill(
            role_id=role_be.id,
            skill_id=skill_python.id,
            importance_weight=0.90,
        )
        rs2 = RoleSkill(
            role_id=role_be.id,
            skill_id=skill_sql.id,
            importance_weight=0.80,
        )
        session.add_all([rs1, rs2])
        await session.commit()


@pytest.mark.asyncio
async def test_list_roles_and_search(async_client: AsyncClient, seed_roles_and_skills):
    response = await async_client.get("/api/v1/roles")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(r["title"] == "Backend Engineer" for r in data["items"])

    # Search
    search_res = await async_client.get("/api/v1/roles?search=backend")
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total"] == 1
    assert search_data["items"][0]["title"] == "Backend Engineer"


@pytest.mark.asyncio
async def test_get_role_details(async_client: AsyncClient, seed_roles_and_skills):
    role_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
    response = await async_client.get(f"/api/v1/roles/{role_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Backend Engineer"
    assert data["description"] == "Designs and builds scalable server-side systems and APIs."


@pytest.mark.asyncio
async def test_get_role_skills_contract(async_client: AsyncClient, seed_roles_and_skills):
    role_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
    response = await async_client.get(f"/api/v1/roles/{role_id}/skills")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == role_id
    assert len(data["role_skills"]) == 2

    # Check weights and skill sub-objects
    skills_map = {rs["skill"]["name"]: rs["importance_weight"] for rs in data["role_skills"]}
    assert skills_map["Python Programming"] == 0.90
    assert skills_map["PostgreSQL"] == 0.80


@pytest.mark.asyncio
async def test_get_role_not_found(async_client: AsyncClient):
    random_id = uuid.uuid4()
    response = await async_client.get(f"/api/v1/roles/{random_id}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
