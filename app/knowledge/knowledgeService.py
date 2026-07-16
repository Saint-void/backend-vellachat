"""Business logic for chatbot knowledge documents."""

import logging
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile

from app.chatbot.chatbotModels import Chatbot
from app.core.coreConfig import settings
from app.core.coreExceptions import NotFoundError, ValidationError
from app.knowledge.knowledgeModels import KnowledgeDocument
from app.knowledge.knowledgeRepository import KnowledgeRepository
from app.knowledge.knowledgeSchemas import KnowledgeTextCreate
from app.knowledge.knowledgeStorage import get_knowledge_storage

logger = logging.getLogger(__name__)


class KnowledgeService:
    allowed_extensions = {".pdf", ".docx", ".txt"}

    def __init__(self, repository: KnowledgeRepository):
        self.repository = repository

    async def list_documents(self, chatbot_id: UUID, owner_id: UUID) -> list[KnowledgeDocument]:
        chatbot = await self._get_owned_chatbot(chatbot_id, owner_id)
        return await self.repository.list_documents(chatbot.id)

    async def create_text_document(self, chatbot_id: UUID, owner_id: UUID, data: KnowledgeTextCreate) -> KnowledgeDocument:
        chatbot = await self._get_owned_chatbot(chatbot_id, owner_id)

        document_id = uuid4()
        storage_name = data.name if data.name.endswith(".txt") else f"{data.name}.txt"
        content_bytes = data.content.encode("utf-8")

        # Write first. Only create the DB row if the write actually
        # succeeds, so we never commit a row pointing at a file that
        # doesn't exist on disk.
        storage_path = await get_knowledge_storage().save(chatbot.id, document_id, storage_name, content_bytes)

        return await self.repository.create_document(
            chatbot.id,
            name=data.name,
            source_type="text",
            mime_type="text/plain",
            storage_path=storage_path,
            file_size=len(content_bytes),
            document_id=document_id,
        )

    async def create_upload_document(self, chatbot_id: UUID, owner_id: UUID, upload: UploadFile) -> KnowledgeDocument:
        chatbot = await self._get_owned_chatbot(chatbot_id, owner_id)
        filename = upload.filename or "document.txt"
        self._validate_filename(filename)

        data = await upload.read()
        if not data:
            raise ValidationError("Uploaded file is empty")
        if len(data) > settings.KNOWLEDGE_MAX_UPLOAD_BYTES:
            raise ValidationError("Uploaded file is too large")

        document_id = uuid4()

        # Same ordering as create_text_document: write first, row second.
        storage_path = await get_knowledge_storage().save(chatbot.id, document_id, filename, data)

        return await self.repository.create_document(
            chatbot.id,
            name=filename,
            source_type="upload",
            mime_type=upload.content_type,
            storage_path=storage_path,
            file_size=len(data),
            document_id=document_id,
        )

    async def get_document(self, chatbot_id: UUID, document_id: UUID, owner_id: UUID) -> KnowledgeDocument:
        chatbot = await self._get_owned_chatbot(chatbot_id, owner_id)
        document = await self.repository.get_document(document_id, chatbot.id)
        if document is None:
            raise NotFoundError("Knowledge document not found")
        return document

    async def delete_document(self, chatbot_id: UUID, document_id: UUID, owner_id: UUID) -> None:
        document = await self.get_document(chatbot_id, document_id, owner_id)
        storage_path = document.storage_path

        # Delete the file before the DB row. If the file delete fails, we
        # abort before touching the DB - the document stays visible and
        # retryable, instead of the DB losing track of a file that never
        # actually got cleaned up on disk.
        try:
            await get_knowledge_storage().delete(storage_path)
        except OSError:
            logger.exception("Failed to delete stored file for document_id=%s", document_id)
            raise

        await self.repository.delete_document(document)

    async def _get_owned_chatbot(self, chatbot_id: UUID, owner_id: UUID) -> Chatbot:
        chatbot = await self.repository.get_owned_chatbot(chatbot_id, owner_id)
        if chatbot is None:
            raise NotFoundError("Chatbot not found")
        return chatbot
    
    # service.py — add this method, and have the router call it instead of get_document
    async def reprocess_document(self, chatbot_id: UUID, document_id: UUID, owner_id: UUID) -> KnowledgeDocument:
        document = await self.get_document(chatbot_id, document_id, owner_id)
        if document.status == "processing":
            raise ValidationError("Document is already processing")
        return document 

    def _validate_filename(self, filename: str) -> None:
        if Path(filename).suffix.lower() not in self.allowed_extensions:
            raise ValidationError("Only PDF, DOCX, and TXT files are supported")