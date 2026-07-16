"""Data access for profiles -- no business logic here, just queries."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.authModels import Profile


class ProfileRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: UUID) -> Profile | None:
        result = await self.db.execute(select(Profile).where(Profile.id == user_id))
        return result.scalar_one_or_none()

    async def create(self, user_id: UUID) -> Profile:
        profile = Profile(id=user_id)
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def update(self, profile: Profile, **fields) -> Profile:
        for key, value in fields.items():
            if value is not None:
                setattr(profile, key, value)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile
