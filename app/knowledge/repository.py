"""Data access for knowledge documents and vector chunks."""

from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.chatbot.models import Chatbot
from app.knowledge.models import KnowledgeDocument


class KnowledgeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_owned_chatbot(self, chatbot_id: UUID, owner_id: UUID) -> Chatbot | None:
        result = await self.db.execute(
            select(Chatbot).where(Chatbot.id == chatbot_id, Chatbot.owner_id == owner_id)
        )
        return result.scalar_one_or_none()

    async def create_document(
        self,
        chatbot_id: UUID,
        name: str,
        source_type: str,
        mime_type: str | None = None,
        storage_path: str | None = None,
    ) -> KnowledgeDocument:
        document = KnowledgeDocument(
            chatbot_id=chatbot_id,
            name=name,
            source_type=source_type,
            mime_type=mime_type,
            storage_path=storage_path,
            status="uploaded",
        )
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def list_documents(self, chatbot_id: UUID) -> list[KnowledgeDocument]:
        result = await self.db.execute(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.chatbot_id == chatbot_id)
            .order_by(KnowledgeDocument.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_document(self, document_id: UUID, chatbot_id: UUID) -> KnowledgeDocument | None:
        result = await self.db.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.id == document_id,
                KnowledgeDocument.chatbot_id == chatbot_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_document_by_id(self, document_id: UUID) -> KnowledgeDocument | None:
        result = await self.db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == document_id))
        return result.scalar_one_or_none()

    async def set_storage_path(self, document: KnowledgeDocument, storage_path: str) -> KnowledgeDocument:
        document.storage_path = storage_path
        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def mark_processing(self, document: KnowledgeDocument) -> KnowledgeDocument:
        document.status = "processing"
        document.error_message = None
        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def mark_ready(self, document: KnowledgeDocument, character_count: int, chunk_count: int) -> KnowledgeDocument:
        document.status = "ready"
        document.error_message = None
        document.character_count = character_count
        document.chunk_count = chunk_count
        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def mark_failed(self, document: KnowledgeDocument, message: str) -> KnowledgeDocument:
        document.status = "failed"
        document.error_message = message[:1000]
        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def delete_document(self, document: KnowledgeDocument) -> None:
        await self.db.delete(document)
        await self.db.commit()

    async def replace_chunks(self, document: KnowledgeDocument, chunks: list[str], embeddings: list[list[float]]) -> None:
        await self.db.execute(
            text("DELETE FROM public.knowledge_chunks WHERE document_id = :document_id"),
            {"document_id": str(document.id)},
        )

        for index, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            await self.db.execute(
                text(
                    """
                    INSERT INTO public.knowledge_chunks (
                        id, document_id, chatbot_id, chunk_index, content, token_count, embedding
                    )
                    VALUES (
                        :id, :document_id, :chatbot_id, :chunk_index, :content, :token_count, (:embedding)::vector
                    )
                    """
                ),
                {
                    "id": str(uuid4()),
                    "document_id": str(document.id),
                    "chatbot_id": str(document.chatbot_id),
                    "chunk_index": index,
                    "content": chunk,
                    "token_count": len(chunk.split()),
                    "embedding": self._vector_literal(embedding),
                },
            )

        await self.db.commit()

    async def search_chunks(self, chatbot_id: UUID, embedding: list[float], limit: int = 5) -> list[dict]:
        result = await self.db.execute(
            text(
                """
                SELECT
                    id,
                    document_id,
                    content,
                    1 - (embedding <=> (:embedding)::vector) AS similarity
                FROM public.knowledge_chunks
                WHERE chatbot_id = :chatbot_id
                ORDER BY embedding <=> (:embedding)::vector
                LIMIT :limit
                """
            ),
            {
                "chatbot_id": str(chatbot_id),
                "embedding": self._vector_literal(embedding),
                "limit": limit,
            },
        )
        return [dict(row._mapping) for row in result]

    def _vector_literal(self, embedding: list[float]) -> str:
        return f"[{','.join(f'{value:.8f}' for value in embedding)}]"
