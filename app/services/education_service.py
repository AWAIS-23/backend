import math
import uuid
import logging
from app.core.exceptions import PermissionDeniedException, ResourceNotFoundException
from app.core.security import AuthenticatedUser
from app.models.education import Education
from app.repositories.education_repo import EducationRepository
from app.schemas.common import PaginatedResponse
from app.schemas.education import EducationCreate, EducationPublic, EducationUpdate

logger = logging.getLogger("rising_skills.services.education")


class EducationService:
    def __init__(self, education_repo: EducationRepository):
        self.education_repo = education_repo

    async def list_my_education(
        self,
        current_user: AuthenticatedUser,
        page: int = 1,
        page_size: int = 100,
    ) -> PaginatedResponse[EducationPublic]:
        skip = (page - 1) * page_size
        profile_id = uuid.UUID(current_user.id)
        items, total = await self.education_repo.list_for_profile(
            profile_id=profile_id,
            skip=skip,
            limit=page_size,
        )
        pages = math.ceil(total / page_size) if total > 0 else 1
        return PaginatedResponse[EducationPublic](
            items=[EducationPublic.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def create_education(
        self,
        current_user: AuthenticatedUser,
        data: EducationCreate,
    ) -> Education:
        education = Education(
            profile_id=uuid.UUID(current_user.id),
            degree=data.degree.strip(),
            institution=data.institution.strip(),
            field_of_study=data.field_of_study,
            start_date=data.start_date,
            end_date=data.end_date,
            grade=data.grade,
            description=data.description,
        )
        created = await self.education_repo.create(education)
        logger.info(f"Education '{created.degree}' created for profile {current_user.id}.")
        return created

    async def update_education(
        self,
        current_user: AuthenticatedUser,
        education_id: uuid.UUID,
        data: EducationUpdate,
    ) -> Education:
        profile_id = uuid.UUID(current_user.id)
        education = await self.education_repo.get_by_id_and_profile(
            education_id=education_id,
            profile_id=profile_id,
        )
        if not education:
            raise ResourceNotFoundException(resource="Education", identifier=education_id)

        updates = data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            if field in ("degree", "institution") and value is not None:
                value = value.strip()
            setattr(education, field, value)

        await self.education_repo.session.flush()
        await self.education_repo.session.refresh(education)
        return education

    async def delete_education(
        self,
        current_user: AuthenticatedUser,
        education_id: uuid.UUID,
    ) -> None:
        profile_id = uuid.UUID(current_user.id)
        education = await self.education_repo.get_by_id_and_profile(
            education_id=education_id,
            profile_id=profile_id,
        )
        if not education:
            raise ResourceNotFoundException(resource="Education", identifier=education_id)
        await self.education_repo.delete(education)
