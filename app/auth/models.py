"""
Profile model.

One row per Supabase Auth user, holding the app-specific fields Auth
itself has no room for. The row is normally created automatically by
a Postgres trigger on auth.users (see the migration) the moment
someone signs up -- this model never creates the row itself in the
normal path. ProfileService.get_profile() creates it lazily as a
fallback only, in case that trigger ever fails to fire.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = {"schema": "public"}

    # No ForeignKey() declared here on purpose: auth.users is a
    # Supabase-managed table outside our migration history, and
    # SQLAlchemy would try (and fail) to manage a table it never
    # created. The actual FK + ON DELETE CASCADE constraint is created
    # in raw SQL in the migration -- this column just needs to match
    # its type.
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    first_name: Mapped[str | None] = mapped_column(nullable=True)
    last_name: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
