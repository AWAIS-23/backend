import pytest
from fastapi import APIRouter, Depends
from httpx import AsyncClient
from app.core.constants import OrgRole, UserRole
from app.core.security import AuthenticatedUser
from app.dependencies.auth import get_current_user
from app.dependencies.roles import require_org_role, require_role
from app.main import app

# Register test routes for verifying security dependencies
mock_security_router = APIRouter(prefix="/api/v1/test-security", tags=["Test Security"])


@mock_security_router.get("/protected")
async def protected_route(current_user: AuthenticatedUser = Depends(get_current_user)):
    return {"message": "authenticated", "user_id": current_user.id, "role": current_user.role}


@mock_security_router.get("/employer-only")
async def employer_only_route(
    current_user: AuthenticatedUser = Depends(require_role([UserRole.EMPLOYER, UserRole.ADMIN]))
):
    return {"message": "employer-access-granted", "user_id": current_user.id}


@mock_security_router.get("/orgs/{org_id}/admin-only")
async def org_admin_route(
    org_id: str,
    current_user: AuthenticatedUser = Depends(
        require_org_role([OrgRole.OWNER, OrgRole.ADMIN], org_id_field="org_id")
    ),
):
    return {"message": "org-admin-access-granted", "org_id": org_id, "user_id": current_user.id}


app.include_router(mock_security_router)


@pytest.mark.asyncio
async def test_protected_route_without_token(async_client: AsyncClient):
    response = await async_client.get("/api/v1/test-security/protected")
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "AUTHENTICATION_REQUIRED"


@pytest.mark.asyncio
async def test_protected_route_with_invalid_token(async_client: AsyncClient):
    response = await async_client.get(
        "/api/v1/test-security/protected",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_protected_route_with_valid_learner_token(async_client: AsyncClient, learner_token: str):
    response = await async_client.get(
        "/api/v1/test-security/protected",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "11111111-1111-1111-1111-111111111111"
    assert data["role"] == "learner"


@pytest.mark.asyncio
async def test_role_guard_rejects_unauthorized_role(async_client: AsyncClient, learner_token: str):
    response = await async_client.get(
        "/api/v1/test-security/employer-only",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_role_guard_allows_authorized_role(async_client: AsyncClient, employer_token: str):
    response = await async_client.get(
        "/api/v1/test-security/employer-only",
        headers={"Authorization": f"Bearer {employer_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "employer-access-granted"


@pytest.mark.asyncio
async def test_org_role_guard_denies_non_member(async_client: AsyncClient, employer_token: str):
    # employer_token has admin role in 'org-100', not 'org-999'
    response = await async_client.get(
        "/api/v1/test-security/orgs/org-999/admin-only",
        headers={"Authorization": f"Bearer {employer_token}"},
    )
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_org_role_guard_allows_member(async_client: AsyncClient, employer_token: str):
    response = await async_client.get(
        "/api/v1/test-security/orgs/org-100/admin-only",
        headers={"Authorization": f"Bearer {employer_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "org-admin-access-granted"


@pytest.mark.asyncio
async def test_org_role_guard_allows_platform_admin_bypass(async_client: AsyncClient, admin_token: str):
    response = await async_client.get(
        "/api/v1/test-security/orgs/org-999/admin-only",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "org-admin-access-granted"
