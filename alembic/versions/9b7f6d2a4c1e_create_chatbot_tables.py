"""create chatbot tables

Revision ID: 9b7f6d2a4c1e
Revises: 3430c802c6e8
Create Date: 2026-07-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9b7f6d2a4c1e"
down_revision = "3430c802c6e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE public.chatbots (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            owner_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
            name VARCHAR(120) NOT NULL,
            business_name VARCHAR(160) NOT NULL,
            industry VARCHAR(120),
            support_goal TEXT,
            website_domain VARCHAR(255),
            tone VARCHAR(50) NOT NULL DEFAULT 'friendly',
            greeting_message TEXT NOT NULL DEFAULT 'Hi! How can I help you today?',
            brand_color VARCHAR(20) NOT NULL DEFAULT '#111111',
            logo_url TEXT,
            handoff_email VARCHAR(255),
            status VARCHAR(30) NOT NULL DEFAULT 'draft',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT chatbots_status_check CHECK (status IN ('draft', 'active', 'paused', 'archived'))
        )
        """
    )
    op.create_index("ix_chatbots_owner_id", "chatbots", ["owner_id"], schema="public")

    op.execute(
        """
        CREATE TABLE public.chatbot_faqs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            chatbot_id UUID NOT NULL REFERENCES public.chatbots(id) ON DELETE CASCADE,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            is_enabled BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.create_index("ix_chatbot_faqs_chatbot_id", "chatbot_faqs", ["chatbot_id"], schema="public")

    op.execute("ALTER TABLE public.chatbots ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.chatbot_faqs ENABLE ROW LEVEL SECURITY")

    op.execute(
        """
        CREATE POLICY "Users can view their own chatbots"
            ON public.chatbots FOR SELECT
            TO authenticated
            USING ((select auth.uid()) = owner_id)
        """
    )
    op.execute(
        """
        CREATE POLICY "Users can insert their own chatbots"
            ON public.chatbots FOR INSERT
            TO authenticated
            WITH CHECK ((select auth.uid()) = owner_id)
        """
    )
    op.execute(
        """
        CREATE POLICY "Users can update their own chatbots"
            ON public.chatbots FOR UPDATE
            TO authenticated
            USING ((select auth.uid()) = owner_id)
        """
    )
    op.execute(
        """
        CREATE POLICY "Users can delete their own chatbots"
            ON public.chatbots FOR DELETE
            TO authenticated
            USING ((select auth.uid()) = owner_id)
        """
    )

    op.execute(
        """
        CREATE POLICY "Users can view FAQ entries for their own chatbots"
            ON public.chatbot_faqs FOR SELECT
            TO authenticated
            USING (
                EXISTS (
                    SELECT 1 FROM public.chatbots
                    WHERE chatbots.id = chatbot_faqs.chatbot_id
                    AND chatbots.owner_id = (select auth.uid())
                )
            )
        """
    )
    op.execute(
        """
        CREATE POLICY "Users can insert FAQ entries for their own chatbots"
            ON public.chatbot_faqs FOR INSERT
            TO authenticated
            WITH CHECK (
                EXISTS (
                    SELECT 1 FROM public.chatbots
                    WHERE chatbots.id = chatbot_faqs.chatbot_id
                    AND chatbots.owner_id = (select auth.uid())
                )
            )
        """
    )
    op.execute(
        """
        CREATE POLICY "Users can update FAQ entries for their own chatbots"
            ON public.chatbot_faqs FOR UPDATE
            TO authenticated
            USING (
                EXISTS (
                    SELECT 1 FROM public.chatbots
                    WHERE chatbots.id = chatbot_faqs.chatbot_id
                    AND chatbots.owner_id = (select auth.uid())
                )
            )
        """
    )
    op.execute(
        """
        CREATE POLICY "Users can delete FAQ entries for their own chatbots"
            ON public.chatbot_faqs FOR DELETE
            TO authenticated
            USING (
                EXISTS (
                    SELECT 1 FROM public.chatbots
                    WHERE chatbots.id = chatbot_faqs.chatbot_id
                    AND chatbots.owner_id = (select auth.uid())
                )
            )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS public.chatbot_faqs")
    op.execute("DROP TABLE IF EXISTS public.chatbots")
