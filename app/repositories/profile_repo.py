import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.profile import Profile
from app.repositories.base import BaseRepository


class ProfileRepository(BaseRepository[Profile]):
    def __init__(self, session: AsyncSession):
        super().__init__(Profile, session)

    async def get_or_create(
        self,
        profile_id: uuid.UUID,
        default_role: str = "learner",
        seed_full_name: str | None = None,
        seed_avatar_url: str | None = None,
    ) -> Profile:
        profile = await self.get_by_id(profile_id)
        if not profile:
            profile = Profile(
                id=profile_id,
                role=default_role,
                full_name=seed_full_name,
                avatar_url=seed_avatar_url,
            )
            self.session.add(profile)
            await self.session.flush()
            await self.session.refresh(profile)
            return profile

        # Backfill null fields from JWT seed values for existing profiles.
        # This self-heals users who signed up before the seed-on-create fix,
        # without overwriting fields the user has explicitly set.
        changed = False
        if profile.full_name is None and seed_full_name:
            profile.full_name = seed_full_name
            changed = True
        if profile.avatar_url is None and seed_avatar_url:
            profile.avatar_url = seed_avatar_url
            changed = True
        if changed:
            await self.session.flush()
            await self.session.refresh(profile)
        return profile
