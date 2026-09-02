import uuid
from fastapi import APIRouter, Depends, Query, status
from app.dependencies.services import get_skill_service
from app.schemas.common import PaginatedResponse
from app.schemas.skill import SkillResponse
from app.services.skill_service import SkillService

router = APIRouter(prefix="/skills", tags=["Skills Taxonomy"])


@router.get(
    "",
    response_model=PaginatedResponse[SkillResponse],
    status_code=status.HTTP_200_OK,
    summary="List and search skills",
    description="Returns a paginated list of skills with optional search, category, and parent filter.",
)
async def list_skills(
    search: str | None = Query(default=None, description="Search term for skill name"),
    category: str | None = Query(default=None, description="Filter by skill category"),
    parent_skill_id: uuid.UUID | None = Query(default=None, description="Filter by parent skill ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
    skill_service: SkillService = Depends(get_skill_service),
) -> PaginatedResponse[SkillResponse]:
    return await skill_service.list_skills(
        search=search,
        category=category,
        parent_skill_id=parent_skill_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{skill_id}",
    response_model=SkillResponse,
    status_code=status.HTTP_200_OK,
    summary="Get skill details",
    description="Returns details for a specific skill.",
)
async def get_skill(
    skill_id: uuid.UUID,
    skill_service: SkillService = Depends(get_skill_service),
) -> SkillResponse:
    skill = await skill_service.get_skill(skill_id)
    return SkillResponse.model_validate(skill)


@router.get(
    "/{skill_id}/children",
    response_model=list[SkillResponse],
    status_code=status.HTTP_200_OK,
    summary="Get child skills",
    description="Returns the sub-skills directly under the specified parent skill.",
)
async def get_child_skills(
    skill_id: uuid.UUID,
    skill_service: SkillService = Depends(get_skill_service),
) -> list[SkillResponse]:
    children = await skill_service.get_children(skill_id)
    return [SkillResponse.model_validate(c) for c in children]
