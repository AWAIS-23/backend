import math
import uuid
import logging
from app.core.exceptions import ResourceConflictException, ResourceNotFoundException
from app.models.role import Role
from app.repositories.role_repo import RoleRepository
from app.repositories.skill_repo import SkillRepository
from app.schemas.common import PaginatedResponse
from app.schemas.role import RoleCreate, RoleResponse, RoleWithSkillsResponse

logger = logging.getLogger("rising_skills.services.role")


class RoleService:
    def __init__(
        self,
        role_repo: RoleRepository,
        skill_repo: SkillRepository,
    ):
        self.role_repo = role_repo
        self.skill_repo = skill_repo

    async def list_roles(
        self,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[RoleResponse]:
        skip = (page - 1) * page_size
        items, total = await self.role_repo.list_roles(search=search, skip=skip, limit=page_size)
        pages = math.ceil(total / page_size) if total > 0 else 1
        return PaginatedResponse[RoleResponse](
            items=[RoleResponse.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def get_role(self, role_id: uuid.UUID) -> Role:
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            raise ResourceNotFoundException(resource="Role", identifier=role_id)
        return role

    async def get_role_with_skills(self, role_id: uuid.UUID) -> RoleWithSkillsResponse:
        role = await self.role_repo.get_role_with_skills(role_id)
        if not role:
            raise ResourceNotFoundException(resource="Role", identifier=role_id)
        return RoleWithSkillsResponse.model_validate(role)

    async def create_role(self, data: RoleCreate) -> Role:
        existing = await self.role_repo.session.execute(
            Role.__table__.select().where(Role.title == data.title.strip())
        )
        if existing.first():
            raise ResourceConflictException(f"A role with title '{data.title}' already exists.")

        role = Role(
            title=data.title.strip(),
            description=data.description,
        )
        return await self.role_repo.create(role)

    async def assign_skill_to_role(
        self,
        role_id: uuid.UUID,
        skill_id: uuid.UUID,
        importance_weight: float = 1.0,
    ):
        await self.get_role(role_id)
        skill = await self.skill_repo.get_by_id(skill_id)
        if not skill:
            raise ResourceNotFoundException(resource="Skill", identifier=skill_id)

        return await self.role_repo.add_role_skill(
            role_id=role_id,
            skill_id=skill_id,
            importance_weight=importance_weight,
        )
