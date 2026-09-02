import uuid
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.verification import Verification
from app.repositories.base import BaseRepository


class VerificationRepository(BaseRepository[Verification]):
    def __init__(self, session: AsyncSession):
        super().__init__(Verification, session)

    async def list_for_evidence(
        self,
        evidence_id: uuid.UUID,
    ) -> Sequence[Verification]:
        stmt = (
            select(Verification)
            .where(Verification.evidence_id == evidence_id)
            .order_by(Verification.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
