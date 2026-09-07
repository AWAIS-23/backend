import uuid
from fastapi import APIRouter, Depends, Query, status
from app.core.security import AuthenticatedUser
from app.dependencies.auth import get_current_user
from app.dependencies.services import get_education_service
from app.schemas.common import PaginatedResponse
from app.schemas.education import EducationCreate, EducationPublic, EducationUpdate
from app.services.education_service import EducationService

router = APIRouter(prefix="/education", tags=["Education"])


@router.get(
    "/me",
    response_model=PaginatedResponse[EducationPublic],
    status_code=status.HTTP_200_OK,
    summary="List my education records",
    description="Returns all education records for the authenticated learner.",
)
async def list_my_education(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
    education_service: EducationService = Depends(get_education_service),
) -> PaginatedResponse[EducationPublic]:
    return await education_service.list_my_education(
        current_user=current_user,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=EducationPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create education record",
    description="Records a new academic background entry for the authenticated learner.",
)
async def create_education(
    data: EducationCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    education_service: EducationService = Depends(get_education_service),
) -> EducationPublic:
    created = await education_service.create_education(
        current_user=current_user,
        data=data,
    )
    return EducationPublic.model_validate(created)


@router.patch(
    "/{education_id}",
    response_model=EducationPublic,
    status_code=status.HTTP_200_OK,
    summary="Update education record",
    description="Updates an existing education record. Restricted to the owner.",
)
async def update_education(
    education_id: uuid.UUID,
    data: EducationUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    education_service: EducationService = Depends(get_education_service),
) -> EducationPublic:
    updated = await education_service.update_education(
        current_user=current_user,
        education_id=education_id,
        data=data,
    )
    return EducationPublic.model_validate(updated)


@router.delete(
    "/{education_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete education record",
    description="Deletes an education record. Restricted to the owner.",
)
async def delete_education(
    education_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    education_service: EducationService = Depends(get_education_service),
) -> None:
    await education_service.delete_education(
        current_user=current_user,
        education_id=education_id,
    )
