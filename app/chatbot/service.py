"""Business logic for chatbot setup and manual FAQ management."""

from uuid import UUID

from app.chatbot.models import Chatbot
from app.chatbot.repository import ChatbotRepository
from app.chatbot.schemas import ChatbotCreate, ChatbotFAQCreate, ChatbotFAQUpdate, ChatbotUpdate
from app.core.exceptions import NotFoundError, ValidationError


class ChatbotService:
    allowed_statuses = {"draft", "active", "paused", "archived"}
    required_chatbot_fields = {"name", "business_name", "tone", "greeting_message", "brand_color", "status"}
    required_faq_fields = {"question", "answer"}

    def __init__(self, repository: ChatbotRepository):
        self.repository = repository

    async def create_chatbot(self, owner_id: UUID, data: ChatbotCreate) -> Chatbot:
        return await self.repository.create(owner_id, **data.model_dump())

    async def list_chatbots(self, owner_id: UUID):
        return await self.repository.list_by_owner(owner_id)

    async def get_chatbot(self, chatbot_id: UUID, owner_id: UUID) -> Chatbot:
        chatbot = await self.repository.get_owned_by_id(chatbot_id, owner_id)
        if chatbot is None:
            raise NotFoundError("Chatbot not found")
        return chatbot

    async def update_chatbot(self, chatbot_id: UUID, owner_id: UUID, data: ChatbotUpdate) -> Chatbot:
        chatbot = await self.get_chatbot(chatbot_id, owner_id)
        fields = data.model_dump(exclude_unset=True)

        if any(field in fields and fields[field] is None for field in self.required_chatbot_fields):
            raise ValidationError("Required chatbot fields cannot be blank")

        if "status" in fields and fields["status"] not in self.allowed_statuses:
            raise ValidationError("Unsupported chatbot status")

        return await self.repository.update(chatbot, **fields)

    async def delete_chatbot(self, chatbot_id: UUID, owner_id: UUID) -> None:
        chatbot = await self.get_chatbot(chatbot_id, owner_id)
        await self.repository.delete(chatbot)

    async def create_faq(self, chatbot_id: UUID, owner_id: UUID, data: ChatbotFAQCreate):
        chatbot = await self.get_chatbot(chatbot_id, owner_id)
        return await self.repository.create_faq(chatbot.id, **data.model_dump())

    async def list_faqs(self, chatbot_id: UUID, owner_id: UUID):
        chatbot = await self.get_chatbot(chatbot_id, owner_id)
        return await self.repository.list_faqs(chatbot.id)

    async def update_faq(self, chatbot_id: UUID, faq_id: UUID, owner_id: UUID, data: ChatbotFAQUpdate):
        chatbot = await self.get_chatbot(chatbot_id, owner_id)
        faq = await self.repository.get_faq_by_id(faq_id, chatbot.id)
        if faq is None:
            raise NotFoundError("FAQ not found")

        fields = data.model_dump(exclude_unset=True)
        if any(field in fields and fields[field] is None for field in self.required_faq_fields):
            raise ValidationError("FAQ question and answer cannot be blank")

        return await self.repository.update_faq(faq, **fields)

    async def delete_faq(self, chatbot_id: UUID, faq_id: UUID, owner_id: UUID) -> None:
        chatbot = await self.get_chatbot(chatbot_id, owner_id)
        faq = await self.repository.get_faq_by_id(faq_id, chatbot.id)
        if faq is None:
            raise NotFoundError("FAQ not found")

        await self.repository.delete_faq(faq)
