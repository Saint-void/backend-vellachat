"""
Declarative base for all ORM models.

Every SQLAlchemy model in every future module (auth, chatbot,
knowledge, billing, ...) inherits from this Base. Alembic's env.py
points its autogenerate diffing at Base.metadata, so a model that
doesn't inherit from here is invisible to migrations.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
