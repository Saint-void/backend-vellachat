"""add file_size to knowledge_documents

Revision ID: c9f3e4d5b6a7
Revises: b8e12b7d5a4f
Create Date: 2026-07-14 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "c9f3e4d5b6a7"
down_revision = "b8e12b7d5a4f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.knowledge_documents ADD COLUMN file_size INTEGER NOT NULL DEFAULT 0")


def downgrade() -> None:
    op.execute("ALTER TABLE public.knowledge_documents DROP COLUMN file_size")
