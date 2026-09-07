import uuid
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.constants import UserRole
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

    async def list_by_role(self, role: UserRole) -> Sequence[Profile]:
        stmt = select(Profile).where(Profile.role == role.value).order_by(Profile.full_name.asc())
        result = await self.session.execute(stmt)
        return result.scalars().all()
