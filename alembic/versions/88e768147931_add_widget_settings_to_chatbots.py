"""add widget_settings to chatbots

Revision ID: 88e768147931
Revises: d1a2b3c4d5e6
Create Date: 2026-07-24 18:20:37.497814

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '88e768147931'
down_revision = 'd1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE public.chatbots
        ADD COLUMN widget_settings JSONB NOT NULL DEFAULT '{}'::jsonb;
    """)



def downgrade():
    op.execute("""
        ALTER TABLE public.chatbots
        DROP COLUMN widget_settings;
    """)
