import uuid
from fastapi import APIRouter, Depends, Query, status
from app.dependencies.services import get_role_service
from app.schemas.common import PaginatedResponse
from app.schemas.role import RoleResponse, RoleWithSkillsResponse
from app.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["Roles & Capabilities"])


@router.get(
    "",
    response_model=PaginatedResponse[RoleResponse],
    status_code=status.HTTP_200_OK,
    summary="List career roles",
    description="Returns a paginated list of standardized career roles with optional search filter.",
)
async def list_roles(
    search: str | None = Query(default=None, description="Search term for role title"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
    role_service: RoleService = Depends(get_role_service),
) -> PaginatedResponse[RoleResponse]:
    return await role_service.list_roles(search=search, page=page, page_size=page_size)


@router.get(
    "/{role_id}",
    response_model=RoleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get career role details",
    description="Returns details for a standardized career role.",
)
async def get_role(
    role_id: uuid.UUID,
    role_service: RoleService = Depends(get_role_service),
) -> RoleResponse:
    role = await role_service.get_role(role_id)
    return RoleResponse.model_validate(role)


@router.get(
    "/{role_id}/skills",
    response_model=RoleWithSkillsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get required skills for role",
    description="Returns the role along with its mapped skills and their importance weights (0.0 to 1.0).",
)
async def get_role_skills(
    role_id: uuid.UUID,
    role_service: RoleService = Depends(get_role_service),
) -> RoleWithSkillsResponse:
    return await role_service.get_role_with_skills(role_id)
