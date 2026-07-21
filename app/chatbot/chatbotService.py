"""Business logic for chatbot setup and manual FAQ management."""

from uuid import UUID

from fastapi import UploadFile

from app.chatbot.chatbotLogoStorage import ChatbotLogoStorage
from app.chatbot.chatbotModels import Chatbot
from app.chatbot.chatbotRepository import ChatbotRepository
from app.chatbot.chatbotSchemas import ChatbotCreate,ChatbotUpdate
from app.core.coreExceptions import NotFoundError, ValidationError
from app.core.coreConfig import settings


class ChatbotService:
    allowed_statuses = {"draft", "active", "paused", "archived"}
    required_chatbot_fields = {"name", "business_name", "tone", "greeting_message", "brand_color", "status"}

    def __init__(self, repository: ChatbotRepository):
        self.repository = repository
        self.logo_storage = ChatbotLogoStorage(settings.CHATBOT_LOGO_STORAGE_DIR, settings.CHATBOT_LOGO_MAX_UPLOAD_BYTES)

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

    async def upload_logo(self, chatbot_id: UUID, owner_id: UUID, file: UploadFile) -> Chatbot:
        """Upload and store a logo for a chatbot."""
        chatbot = await self.get_chatbot(chatbot_id, owner_id)

        if not file.content_type or file.content_type not in ChatbotLogoStorage.VALID_TYPES:
            raise ValidationError(f"Unsupported image type. Must be PNG, JPEG, WebP, or GIF.")

        if file.size and file.size > settings.CHATBOT_LOGO_MAX_UPLOAD_BYTES:
            raise ValidationError(f"Logo must be smaller than {settings.CHATBOT_LOGO_MAX_UPLOAD_BYTES / (1024 * 1024):.0f} MB.")

        # Read file content
        content = await file.read()

        # Store the logo
        logo_path = await self.logo_storage.replace(chatbot_id, file.content_type, content)

        # Update chatbot with logo URL (store relative path)
        logo_url = f"/api/v1/chatbots/{chatbot_id}/logo"
        return await self.repository.update(chatbot, logo_url=logo_url)

    async def delete_logo(self, chatbot_id: UUID, owner_id: UUID) -> Chatbot:
        """Delete the logo for a chatbot."""
        chatbot = await self.get_chatbot(chatbot_id, owner_id)

        if chatbot.logo_url:
            logo_path = await self.logo_storage.resolve(chatbot_id)
            if logo_path:
                await self.logo_storage.delete(str(logo_path))

        # Update chatbot to remove logo URL
        return await self.repository.update(chatbot, logo_url=None)