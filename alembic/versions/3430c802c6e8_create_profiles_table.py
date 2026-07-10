"""create profiles table

Revision ID: 3430c802c6e8
Revises: 
Create Date: 2026-07-09 19:32:25.187382

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3430c802c6e8'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Table ---
    # FK to auth.users is written as raw SQL, not sa.ForeignKey() in
    # the model -- see the note in app/auth/models.py for why.
    op.execute(
        """
        CREATE TABLE public.profiles (
            id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
            first_name TEXT,
            last_name TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    # --- Auto-create a profile the moment someone signs up ---
    # SECURITY DEFINER so the trigger can write to public.profiles
    # regardless of who's inserting into auth.users (that's Supabase's
    # own internal role, not ours). SET search_path pins name
    # resolution to public, standard hardening for SECURITY DEFINER
    # functions so they can't be tricked by a caller-controlled
    # search_path. The EXCEPTION block matters: Supabase's own docs
    # warn that a failing trigger can block the signup itself -- this
    # logs a warning and lets the signup succeed regardless.
    # ProfileService.get_profile() creates the row lazily as a
    # fallback if it's ever missing.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.handle_new_user()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO public.profiles (id, first_name, last_name)
            VALUES (
                NEW.id,
                COALESCE(
                    NEW.raw_user_meta_data->>'first_name',
                    split_part(NEW.raw_user_meta_data->>'full_name', ' ', 1),
                    split_part(NEW.raw_user_meta_data->>'name', ' ', 1)
                ),
                NEW.raw_user_meta_data->>'last_name'
            );
            RETURN NEW;
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'handle_new_user failed for %: %', NEW.id, SQLERRM;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;
        """
    )
    op.execute(
        """
        CREATE TRIGGER on_auth_user_created
            AFTER INSERT ON auth.users
            FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
        """
    )

    # --- Row Level Security ---
    # Our own backend connects with a role that bypasses RLS, so this
    # isn't for us -- it's for the auto-generated Supabase Data API.
    # Any table in the public schema is reachable at
    # https://<project>.supabase.co/rest/v1/<table> using the public
    # anon/publishable key unless RLS says otherwise. Without this,
    # someone could read or edit every user's profile directly through
    # that API, completely bypassing our FastAPI backend.
    op.execute("ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY "Users can view their own profile"
            ON public.profiles FOR SELECT
            TO authenticated
            USING ((select auth.uid()) = id)
        """
    )
    op.execute(
        """
        CREATE POLICY "Users can update their own profile"
            ON public.profiles FOR UPDATE
            TO authenticated
            USING ((select auth.uid()) = id)
        """
    )
    op.execute(
        """
        CREATE POLICY "Users can insert their own profile"
            ON public.profiles FOR INSERT
            TO authenticated
            WITH CHECK ((select auth.uid()) = id)
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users")
    op.execute("DROP FUNCTION IF EXISTS public.handle_new_user()")
    op.execute("DROP TABLE IF EXISTS public.profiles")
