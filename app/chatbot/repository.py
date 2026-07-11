"""Data access for chatbots and manual FAQ entries."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chatbot.models import Chatbot, ChatbotFAQ


class ChatbotRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, owner_id: UUID, **fields) -> Chatbot:
        chatbot = Chatbot(owner_id=owner_id, **fields)
        self.db.add(chatbot)
        await self.db.commit()
        await self.db.refresh(chatbot)
        return chatbot

    async def list_by_owner(self, owner_id: UUID) -> list[Chatbot]:
        result = await self.db.execute(
            select(Chatbot).where(Chatbot.owner_id == owner_id).order_by(Chatbot.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_owned_by_id(self, chatbot_id: UUID, owner_id: UUID) -> Chatbot | None:
        result = await self.db.execute(
            select(Chatbot).where(Chatbot.id == chatbot_id, Chatbot.owner_id == owner_id)
        )
        return result.scalar_one_or_none()

    async def update(self, chatbot: Chatbot, **fields) -> Chatbot:
        for key, value in fields.items():
            setattr(chatbot, key, value)
        await self.db.commit()
        await self.db.refresh(chatbot)
        return chatbot

    async def delete(self, chatbot: Chatbot) -> None:
        await self.db.delete(chatbot)
        await self.db.commit()

    async def create_faq(self, chatbot_id: UUID, **fields) -> ChatbotFAQ:
        faq = ChatbotFAQ(chatbot_id=chatbot_id, **fields)
        self.db.add(faq)
        await self.db.commit()
        await self.db.refresh(faq)
        return faq

    async def list_faqs(self, chatbot_id: UUID) -> list[ChatbotFAQ]:
        result = await self.db.execute(
            select(ChatbotFAQ).where(ChatbotFAQ.chatbot_id == chatbot_id).order_by(ChatbotFAQ.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_faq_by_id(self, faq_id: UUID, chatbot_id: UUID) -> ChatbotFAQ | None:
        result = await self.db.execute(
            select(ChatbotFAQ).where(ChatbotFAQ.id == faq_id, ChatbotFAQ.chatbot_id == chatbot_id)
        )
        return result.scalar_one_or_none()

    async def update_faq(self, faq: ChatbotFAQ, **fields) -> ChatbotFAQ:
        for key, value in fields.items():
            setattr(faq, key, value)
        await self.db.commit()
        await self.db.refresh(faq)
        return faq

    async def delete_faq(self, faq: ChatbotFAQ) -> None:
        await self.db.delete(faq)
        await self.db.commit()
