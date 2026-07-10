"""
Alembic environment configuration.

Runs migrations against DIRECT_DATABASE_URL (the unpooled connection),
never DATABASE_URL -- see the note in app/core/config.py for why.
Uses SQLAlchemy's async engine since the rest of the app is async; the
migration script itself still runs inside connection.run_sync(),
because Alembic's migration machinery is synchronous even in async
projects.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.database.base import Base

# Import every module's models here so Base.metadata knows about them
# for autogenerate.
from app.auth.models import Profile  # noqa
# from app.chatbot.models import Chatbot  # noqa

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

config.set_main_option("sqlalchemy.url", settings.DIRECT_DATABASE_URL)


def run_migrations_offline() -> None:
    context.configure(
        url=settings.DIRECT_DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
