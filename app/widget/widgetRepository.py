"""Data access for public widget conversations."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.chatbot.chatbotModels import Chatbot
from app.widget.widgetModels import WidgetConversation, WidgetMessage


class WidgetRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_chatbot(self, chatbot_id: UUID) -> Chatbot | None:
        result = await self.db.execute(select(Chatbot).where(Chatbot.id == chatbot_id))
        return result.scalar_one_or_none()

    async def create_conversation(self, chatbot_id: UUID, site_origin: str, visitor_id: str | None) -> WidgetConversation:
        conversation = WidgetConversation(chatbot_id=chatbot_id, site_origin=site_origin, visitor_id=visitor_id)
        self.db.add(conversation)
        await self.db.commit()
        return conversation

    async def get_conversation(self, conversation_id: UUID, chatbot_id: UUID) -> WidgetConversation | None:
        result = await self.db.execute(
            select(WidgetConversation).where(
                WidgetConversation.id == conversation_id,
                WidgetConversation.chatbot_id == chatbot_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_messages(self, conversation_id: UUID) -> list[WidgetMessage]:
        result = await self.db.execute(
            select(WidgetMessage)
            .where(WidgetMessage.conversation_id == conversation_id)
            .order_by(WidgetMessage.created_at.asc())
        )
        return list(result.scalars().all())

    async def create_message(
        self,
        conversation: WidgetConversation,
        role: str,
        content: str
    ) -> WidgetMessage:
        message = WidgetMessage(
            conversation_id=conversation.id,
            role=role,
            content=content
        )
        conversation.updated_at = datetime.now(timezone.utc)
        self.db.add(message)
        await self.db.commit()
        return message

    async def expire_conversations_before(self, cutoff_time: datetime) -> int:
        """Mark all conversations with status='open' and updated_at < cutoff_time as 'expired'.

        Returns the number of conversations marked as expired.
        """
        result = await self.db.execute(
            update(WidgetConversation)
            .where(
                WidgetConversation.status == "open",
                WidgetConversation.updated_at < cutoff_time,
            )
            .values(status="expired")
        )
        await self.db.commit()
        return result.rowcount or 0

    async def close_conversation(self, conversation: WidgetConversation) -> None:
        """Mark a conversation as closed."""
        conversation.status = "closed"
        self.db.add(conversation)
        await self.db.commit()

    async def create_exchange(
        self,
        conversation: WidgetConversation,
        visitor_content: str,
        assistant_content: str,
    ) -> tuple[WidgetMessage, WidgetMessage]:
        visitor_message = WidgetMessage(
            conversation_id=conversation.id, role="visitor", content=visitor_content
        )
        assistant_message = WidgetMessage(
            conversation_id=conversation.id, role="assistant", content=assistant_content
        )
        conversation.updated_at = datetime.now(timezone.utc)
        self.db.add_all([visitor_message, assistant_message])
        await self.db.commit()
        return visitor_message, assistant_message
