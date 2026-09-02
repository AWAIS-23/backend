import uuid
import logging
from app.core.exceptions import ResourceNotFoundException
from app.models.profile import Profile
from app.repositories.profile_repo import ProfileRepository
from app.schemas.profile import ProfileUpdate

logger = logging.getLogger("rising_skills.services.profile")


class ProfileService:
    def __init__(self, profile_repo: ProfileRepository):
        self.profile_repo = profile_repo

    async def get_or_initialize_profile(
        self,
        profile_id: uuid.UUID,
        default_role: str = "learner",
    ) -> Profile:
        """
        Retrieves user profile, automatically initializing on first authenticated login.
        """
        profile = await self.profile_repo.get_or_create(profile_id, default_role=default_role)
        return profile

    async def get_profile(self, profile_id: uuid.UUID) -> Profile:
        profile = await self.profile_repo.get_by_id(profile_id)
        if not profile:
            raise ResourceNotFoundException(resource="Profile", identifier=profile_id)
        return profile

    async def update_profile(
        self,
        profile_id: uuid.UUID,
        update_data: ProfileUpdate,
    ) -> Profile:
        """
        Updates editable profile fields. Role and ID modification are strictly prevented.
        """
        profile = await self.get_or_initialize_profile(profile_id)

        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(profile, field, value)

        await self.profile_repo.session.flush()
        await self.profile_repo.session.refresh(profile)
        logger.info(f"Profile updated for user '{profile_id}'")
        return profile
