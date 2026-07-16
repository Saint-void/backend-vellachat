"""fix embedding dimension for nomic-embed-text

Revision ID: d1a2b3c4d5e6
Revises: c9f3e4d5b6a7
Create Date: 2026-07-15 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "d1a2b3c4d5e6"
down_revision = "c9f3e4d5b6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # nomic-embed-text produces 768-dim vectors, not 1536.
    # pgvector won't let us insert 768-dim data into a 1536-dim column,
    # so we must alter the column, wipe existing chunks (if any have the
    # wrong dimension), and rebuild the ivfflat index.
    op.execute("DELETE FROM public.knowledge_chunks")
    op.execute("DROP INDEX IF EXISTS public.ix_knowledge_chunks_embedding")
    op.execute("ALTER TABLE public.knowledge_chunks ALTER COLUMN embedding TYPE vector(768)")
    op.execute(
        """
        CREATE INDEX ix_knowledge_chunks_embedding
            ON public.knowledge_chunks
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM public.knowledge_chunks")
    op.execute("DROP INDEX IF EXISTS public.ix_knowledge_chunks_embedding")
    op.execute("ALTER TABLE public.knowledge_chunks ALTER COLUMN embedding TYPE vector(1536)")
    op.execute(
        """
        CREATE INDEX ix_knowledge_chunks_embedding
            ON public.knowledge_chunks
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """
    )
