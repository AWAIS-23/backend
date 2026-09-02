import uuid
from fastapi import APIRouter, Depends, status
from app.core.security import AuthenticatedUser
from app.dependencies.auth import get_current_user
from app.dependencies.services import get_profile_service
from app.schemas.profile import ProfileResponse, ProfileUpdate
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/profiles", tags=["Profiles"])


@router.get(
    "/me",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="Retrieves the profile of the authenticated user. Automatically initializes profile if first login.",
)
async def get_my_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    profile = await profile_service.get_or_initialize_profile(
        profile_id=uuid.UUID(current_user.id),
        default_role=current_user.role.value,
    )
    return ProfileResponse.model_validate(profile)


@router.patch(
    "/me",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current user profile",
    description="Updates editable profile attributes (name, avatar, bio). Role and ID cannot be updated via this endpoint.",
)
async def update_my_profile(
    payload: ProfileUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    profile = await profile_service.update_profile(
        profile_id=uuid.UUID(current_user.id),
        update_data=payload,
    )
    return ProfileResponse.model_validate(profile)
