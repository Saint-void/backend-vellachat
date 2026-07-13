"""create knowledge tables

Revision ID: b8e12b7d5a4f
Revises: 4f6d2d1c8c1a
Create Date: 2026-07-13 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "b8e12b7d5a4f"
down_revision = "4f6d2d1c8c1a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute(
        """
        CREATE TABLE public.knowledge_documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            chatbot_id UUID NOT NULL REFERENCES public.chatbots(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            source_type VARCHAR(40) NOT NULL,
            mime_type VARCHAR(160),
            storage_path TEXT,
            status VARCHAR(30) NOT NULL DEFAULT 'uploaded',
            error_message TEXT,
            character_count INTEGER NOT NULL DEFAULT 0,
            chunk_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT knowledge_documents_status_check CHECK (status IN ('uploaded', 'processing', 'ready', 'failed'))
        )
        """
    )
    op.create_index("ix_knowledge_documents_chatbot_id", "knowledge_documents", ["chatbot_id"], schema="public")

    op.execute(
        """
        CREATE TABLE public.knowledge_chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID NOT NULL REFERENCES public.knowledge_documents(id) ON DELETE CASCADE,
            chatbot_id UUID NOT NULL REFERENCES public.chatbots(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            token_count INTEGER NOT NULL DEFAULT 0,
            embedding vector(1536) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"], schema="public")
    op.create_index("ix_knowledge_chunks_chatbot_id", "knowledge_chunks", ["chatbot_id"], schema="public")
    op.execute(
        """
        CREATE INDEX ix_knowledge_chunks_embedding
            ON public.knowledge_chunks
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """
    )

    op.execute("ALTER TABLE public.knowledge_documents ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.knowledge_chunks ENABLE ROW LEVEL SECURITY")

    op.execute(
        """
        CREATE POLICY "Users can manage documents for their own chatbots"
            ON public.knowledge_documents FOR ALL
            TO authenticated
            USING (
                EXISTS (
                    SELECT 1 FROM public.chatbots
                    WHERE chatbots.id = knowledge_documents.chatbot_id
                    AND chatbots.owner_id = (select auth.uid())
                )
            )
            WITH CHECK (
                EXISTS (
                    SELECT 1 FROM public.chatbots
                    WHERE chatbots.id = knowledge_documents.chatbot_id
                    AND chatbots.owner_id = (select auth.uid())
                )
            )
        """
    )
    op.execute(
        """
        CREATE POLICY "Users can manage chunks for their own chatbots"
            ON public.knowledge_chunks FOR ALL
            TO authenticated
            USING (
                EXISTS (
                    SELECT 1 FROM public.chatbots
                    WHERE chatbots.id = knowledge_chunks.chatbot_id
                    AND chatbots.owner_id = (select auth.uid())
                )
            )
            WITH CHECK (
                EXISTS (
                    SELECT 1 FROM public.chatbots
                    WHERE chatbots.id = knowledge_chunks.chatbot_id
                    AND chatbots.owner_id = (select auth.uid())
                )
            )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS public.knowledge_chunks")
    op.execute("DROP TABLE IF EXISTS public.knowledge_documents")
