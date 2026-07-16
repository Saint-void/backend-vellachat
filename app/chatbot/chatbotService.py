"""Business logic for chatbot setup and manual FAQ management."""

from uuid import UUID

from app.chatbot.chatbotModels import Chatbot
from app.chatbot.chatbotRepository import ChatbotRepository
from app.chatbot.chatbotSchemas import ChatbotCreate,ChatbotUpdate
from app.core.coreExceptions import NotFoundError, ValidationError


class ChatbotService:
    allowed_statuses = {"draft", "active", "paused", "archived"}
    required_chatbot_fields = {"name", "business_name", "tone", "greeting_message", "brand_color", "status"}

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

    