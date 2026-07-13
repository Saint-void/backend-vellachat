"""Business logic for chatbot knowledge documents."""

from pathlib import Path
from uuid import UUID

from fastapi import UploadFile

from app.chatbot.models import Chatbot
from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.knowledge.models import KnowledgeDocument
from app.knowledge.repository import KnowledgeRepository
from app.knowledge.schemas import KnowledgeTextCreate
from app.knowledge.storage import get_knowledge_storage


class KnowledgeService:
    allowed_extensions = {".pdf", ".docx", ".txt"}

    def __init__(self, repository: KnowledgeRepository):
        self.repository = repository

    async def list_documents(self, chatbot_id: UUID, owner_id: UUID) -> list[KnowledgeDocument]:
        chatbot = await self._get_owned_chatbot(chatbot_id, owner_id)
        return await self.repository.list_documents(chatbot.id)

    async def create_text_document(self, chatbot_id: UUID, owner_id: UUID, data: KnowledgeTextCreate) -> KnowledgeDocument:
        chatbot = await self._get_owned_chatbot(chatbot_id, owner_id)
        document = await self.repository.create_document(
            chatbot.id,
            name=data.name,
            source_type="text",
            mime_type="text/plain",
        )
        storage_path = await get_knowledge_storage().save(
            chatbot.id,
            document.id,
            f"{document.name}.txt" if not document.name.endswith(".txt") else document.name,
            data.content.encode("utf-8"),
        )
        return await self.repository.set_storage_path(document, storage_path)

    async def create_upload_document(self, chatbot_id: UUID, owner_id: UUID, upload: UploadFile) -> KnowledgeDocument:
        chatbot = await self._get_owned_chatbot(chatbot_id, owner_id)
        filename = upload.filename or "document.txt"
        self._validate_filename(filename)

        data = await upload.read()
        if not data:
            raise ValidationError("Uploaded file is empty")
        if len(data) > settings.KNOWLEDGE_MAX_UPLOAD_BYTES:
            raise ValidationError("Uploaded file is too large")

        document = await self.repository.create_document(
            chatbot.id,
            name=filename,
            source_type="upload",
            mime_type=upload.content_type,
        )
        storage_path = await get_knowledge_storage().save(chatbot.id, document.id, filename, data)
        return await self.repository.set_storage_path(document, storage_path)

    async def get_document(self, chatbot_id: UUID, document_id: UUID, owner_id: UUID) -> KnowledgeDocument:
        chatbot = await self._get_owned_chatbot(chatbot_id, owner_id)
        document = await self.repository.get_document(document_id, chatbot.id)
        if document is None:
            raise NotFoundError("Knowledge document not found")
        return document

    async def delete_document(self, chatbot_id: UUID, document_id: UUID, owner_id: UUID) -> None:
        document = await self.get_document(chatbot_id, document_id, owner_id)
        storage_path = document.storage_path
        await self.repository.delete_document(document)
        await get_knowledge_storage().delete(storage_path)

    async def _get_owned_chatbot(self, chatbot_id: UUID, owner_id: UUID) -> Chatbot:
        chatbot = await self.repository.get_owned_chatbot(chatbot_id, owner_id)
        if chatbot is None:
            raise NotFoundError("Chatbot not found")
        return chatbot

    def _validate_filename(self, filename: str) -> None:
        if Path(filename).suffix.lower() not in self.allowed_extensions:
            raise ValidationError("Only PDF, DOCX, and TXT files are supported")
