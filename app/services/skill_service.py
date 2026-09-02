import math
import uuid
import logging
from typing import Sequence
from app.core.exceptions import ResourceConflictException, ResourceNotFoundException
from app.models.skill import Skill
from app.repositories.skill_repo import SkillRepository
from app.schemas.common import PaginatedResponse
from app.schemas.skill import SkillCreate, SkillResponse

logger = logging.getLogger("rising_skills.services.skill")


class SkillService:
    def __init__(self, skill_repo: SkillRepository):
        self.skill_repo = skill_repo

    async def list_skills(
        self,
        search: str | None = None,
        category: str | None = None,
        parent_skill_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[SkillResponse]:
        skip = (page - 1) * page_size
        items, total = await self.skill_repo.list_skills(
            search=search,
            category=category,
            parent_skill_id=parent_skill_id,
            skip=skip,
            limit=page_size,
        )
        pages = math.ceil(total / page_size) if total > 0 else 1
        return PaginatedResponse[SkillResponse](
            items=[SkillResponse.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def get_skill(self, skill_id: uuid.UUID) -> Skill:
        skill = await self.skill_repo.get_by_id(skill_id)
        if not skill:
            raise ResourceNotFoundException(resource="Skill", identifier=skill_id)
        return skill

    async def get_children(self, skill_id: uuid.UUID) -> Sequence[Skill]:
        await self.get_skill(skill_id)  # Ensure parent exists
        return await self.skill_repo.get_children(skill_id)

    async def create_skill(self, data: SkillCreate) -> Skill:
        existing = await self.skill_repo.get_by_name(data.name)
        if existing:
            raise ResourceConflictException(f"A skill with name '{data.name}' already exists.")

        if data.parent_skill_id:
            parent = await self.skill_repo.get_by_id(data.parent_skill_id)
            if not parent:
                raise ResourceNotFoundException(resource="Parent Skill", identifier=data.parent_skill_id)

        skill = Skill(
            name=data.name.strip(),
            category=data.category.strip(),
            parent_skill_id=data.parent_skill_id,
        )
        return await self.skill_repo.create(skill)
