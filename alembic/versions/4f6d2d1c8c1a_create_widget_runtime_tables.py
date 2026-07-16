"""create widget runtime tables

Revision ID: 4f6d2d1c8c1a
Revises: 9b7f6d2a4c1e
Create Date: 2026-07-11 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "4f6d2d1c8c1a"
down_revision = "9b7f6d2a4c1e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE public.widget_conversations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            chatbot_id UUID NOT NULL REFERENCES public.chatbots(id) ON DELETE CASCADE,
            visitor_id VARCHAR(255),
            site_origin VARCHAR(255) NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'open',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.create_index("ix_widget_conversations_chatbot_id", "widget_conversations", ["chatbot_id"], schema="public")

    op.execute(
        """
        CREATE TABLE public.widget_messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            conversation_id UUID NOT NULL REFERENCES public.widget_conversations(id) ON DELETE CASCADE
            role VARCHAR(30) NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.create_index("ix_widget_messages_conversation_id", "widget_messages", ["conversation_id"], schema="public")
    op.create_index("ix_widget_messages_matched_faq_id", "widget_messages", ["matched_faq_id"], schema="public")

    op.execute("ALTER TABLE public.widget_conversations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.widget_messages ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS public.widget_messages")
    op.execute("DROP TABLE IF EXISTS public.widget_conversations")
