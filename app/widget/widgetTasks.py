"""Background tasks for widget conversations."""

import logging
from datetime import datetime, timedelta, timezone

from app.database.databaseSession import AsyncSessionLocal
from app.widget.widgetRepository import WidgetRepository

logger = logging.getLogger(__name__)


async def expire_inactive_conversations(timeout_minutes: int = 30) -> int:
    """Mark conversations as expired if they've been inactive for longer than timeout.

    Returns the number of conversations marked as expired.
    """
    async with AsyncSessionLocal() as db:
        repository = WidgetRepository(db)
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)

        try:
            count = await repository.expire_conversations_before(cutoff_time)
            logger.info("widget_conversation_expiry expired_count=%d", count)
            return count
        except Exception as exc:
            logger.exception("Failed to expire inactive conversations")
            return 0
