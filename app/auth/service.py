"""Business logic for the profile module."""

from uuid import UUID

from app.auth.repository import ProfileRepository
from app.auth.schemas import ProfileUpdate


class ProfileService:
    def __init__(self, repository: ProfileRepository):
        self.repository = repository

    async def get_profile(self, user_id: UUID):
        """
        Fetches the caller's profile, creating it if it doesn't exist.

        The normal path is: the auth.users trigger already created
        this row the moment the user signed up, so this is a plain
        read. The lazy-create fallback exists because Supabase's own
        docs are explicit that a trigger failure could otherwise block
        or orphan a signup -- this makes that recoverable instead of
        a stuck account with no profile and no way to get one.
        """
        profile = await self.repository.get_by_id(user_id)
        if profile is None:
            profile = await self.repository.create(user_id)
        return profile

    async def update_profile(self, user_id: UUID, data: ProfileUpdate):
        profile = await self.get_profile(user_id)
        return await self.repository.update(profile, **data.model_dump(exclude_unset=True))
