import uuid
from fastapi import APIRouter, Depends, status
from app.core.constants import UserRole
from app.core.security import AuthenticatedUser
from app.dependencies.auth import get_current_user
from app.dependencies.roles import require_role
from app.dependencies.services import get_organization_service
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationMemberResponse,
    OrganizationResponse,
)
from app.services.organization_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an organization",
    description="Creates a new organization profile and assigns the authenticated employer as the Owner.",
)
async def create_organization(
    payload: OrganizationCreate,
    current_user: AuthenticatedUser = Depends(require_role([UserRole.EMPLOYER, UserRole.ADMIN])),
    org_service: OrganizationService = Depends(get_organization_service),
) -> OrganizationResponse:
    org = await org_service.create_organization(
        creator_id=uuid.UUID(current_user.id),
        data=payload,
    )
    return OrganizationResponse.model_validate(org)


@router.get(
    "",
    response_model=list[OrganizationResponse],
    status_code=status.HTTP_200_OK,
    summary="List organizations for authenticated user",
    description="Returns organizations where the authenticated user is a member.",
)
async def list_my_organizations(
    current_user: AuthenticatedUser = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_organization_service),
) -> list[OrganizationResponse]:
    orgs = await org_service.list_user_organizations(user_id=uuid.UUID(current_user.id))
    return [OrganizationResponse.model_validate(o) for o in orgs]


@router.get(
    "/{organization_id}",
    response_model=OrganizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get organization details",
    description="Returns organization details. Restricted to organization members or platform administrators.",
)
async def get_organization(
    organization_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_organization_service),
) -> OrganizationResponse:
    is_admin = current_user.role == UserRole.ADMIN
    org = await org_service.get_organization(
        org_id=organization_id,
        user_id=uuid.UUID(current_user.id),
        is_platform_admin=is_admin,
    )
    return OrganizationResponse.model_validate(org)


@router.get(
    "/{organization_id}/members",
    response_model=list[OrganizationMemberResponse],
    status_code=status.HTTP_200_OK,
    summary="List organization members",
    description="Returns the roster of members belonging to the organization. Restricted to organization members.",
)
async def list_organization_members(
    organization_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_organization_service),
) -> list[OrganizationMemberResponse]:
    is_admin = current_user.role == UserRole.ADMIN
    members = await org_service.list_members(
        org_id=organization_id,
        user_id=uuid.UUID(current_user.id),
        is_platform_admin=is_admin,
    )
    return [OrganizationMemberResponse.model_validate(m) for m in members]
