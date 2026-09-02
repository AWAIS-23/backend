import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.profile import Profile
from app.repositories.base import BaseRepository


class ProfileRepository(BaseRepository[Profile]):
    def __init__(self, session: AsyncSession):
        super().__init__(Profile, session)

    async def get_or_create(self, profile_id: uuid.UUID, default_role: str = "learner") -> Profile:
        profile = await self.get_by_id(profile_id)
        if not profile:
            profile = Profile(id=profile_id, role=default_role)
            self.session.add(profile)
            await self.session.flush()
            await self.session.refresh(profile)
        return profile
