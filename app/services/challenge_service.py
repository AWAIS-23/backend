import math
import uuid
import logging
from app.core.constants import ChallengeStatus, UserRole
from app.core.exceptions import PermissionDeniedException, ResourceNotFoundException
from app.models.challenge import Challenge
from app.repositories.challenge_repo import ChallengeRepository
from app.schemas.challenge import (
    ChallengeCreate,
    ChallengeDetailPublic,
    ChallengePublic,
    ChallengeSkillPublic,
)
from app.schemas.common import PaginatedResponse

logger = logging.getLogger("rising_skills.services.challenge")


class ChallengeService:
    def __init__(self, challenge_repo: ChallengeRepository):
        self.challenge_repo = challenge_repo

    async def list_challenges(
        self,
        organization_id: uuid.UUID | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
        user_role: UserRole = UserRole.LEARNER,
    ) -> PaginatedResponse[ChallengePublic]:
        skip = (page - 1) * page_size
        # Learners only see PUBLISHED challenges; Admins/Employers can see all when filtered appropriately
        status_filter = ChallengeStatus.PUBLISHED if user_role == UserRole.LEARNER else None

        items, total = await self.challenge_repo.list_challenges(
            status=status_filter,
            organization_id=organization_id,
            search=search,
            skip=skip,
            limit=page_size,
        )
        pages = math.ceil(total / page_size) if total > 0 else 1

        return PaginatedResponse[ChallengePublic](
            items=[ChallengePublic.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def get_challenge_detail(
        self,
        challenge_id: uuid.UUID,
        user_role: UserRole = UserRole.LEARNER,
    ) -> ChallengeDetailPublic:
        challenge = await self.challenge_repo.get_with_skills(challenge_id)
        if not challenge:
            raise ResourceNotFoundException(resource="Challenge", identifier=challenge_id)

        if user_role == UserRole.LEARNER and challenge.status != ChallengeStatus.PUBLISHED:
            raise PermissionDeniedException("This challenge is not currently published or available.")

        skills_public = []
        for cs in challenge.challenge_skills:
            skills_public.append(
                ChallengeSkillPublic(
                    skill_id=cs.skill_id,
                    skill_name=cs.skill.name if cs.skill else "Unknown Skill",
                    importance_weight=cs.importance_weight,
                )
            )

        detail = ChallengeDetailPublic.model_validate(challenge)
        detail.skills = skills_public
        return detail

    async def create_challenge(
        self,
        creator_id: uuid.UUID,
        data: ChallengeCreate,
    ) -> Challenge:
        challenge = Challenge(
            title=data.title.strip(),
            description=data.description,
            instructions=data.instructions,
            difficulty=data.difficulty,
            status=data.status,
            created_by=creator_id,
            organization_id=data.organization_id,
            role_id=data.role_id,
            time_limit_seconds=data.time_limit_seconds,
            submission_deadline=data.submission_deadline,
        )

        skill_items = [(s.skill_id, s.importance_weight) for s in data.skills]
        created = await self.challenge_repo.create_with_skills(challenge, skill_items)
        logger.info(f"Challenge '{created.title}' created with {len(skill_items)} skills mapped.")
        return created
