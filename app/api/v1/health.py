"""
Health check endpoints.

/health confirms the process is up. /health/db additionally confirms
the database is reachable -- this is the one query in the whole
codebase that exists purely to prove the skeleton works, and it's what
Railway/Render will poll to decide if the service is alive.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict:
    return {"status": "ok"}


@router.get("/health/db", status_code=status.HTTP_200_OK)
async def health_db(db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable"}
