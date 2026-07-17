"""Data access for knowledge documents and vector chunks."""

import re
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.chatbot.chatbotModels import Chatbot
from app.knowledge.knowledgeModels import KnowledgeDocument


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
        file_size: int = 0,
        document_id: UUID | None = None,
    ) -> KnowledgeDocument:
        """Create the document row.

        Callers that write a file to storage should generate the id up
        front, save the file, and only call this once the write succeeds
        (passing storage_path + document_id) - see KnowledgeService. That
        ordering means we never commit a row pointing at a file that never
        made it to disk.
        """
        document = KnowledgeDocument(
            id=document_id or uuid4(),
            chatbot_id=chatbot_id,
            name=name,
            source_type=source_type,
            mime_type=mime_type,
            storage_path=storage_path,
            file_size=file_size,
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

    async def list_stuck_processing(self, older_than: datetime) -> list[KnowledgeDocument]:
        """Documents still 'processing' since before `older_than`.

        `updated_at` gets bumped by mark_processing()'s commit, so it
        doubles as "when processing started" - no extra column needed.
        Used by tasks.sweep_stuck_documents to recover from a Render
        restart/crash that killed an in-flight background task.
        """
        result = await self.db.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.status == "processing",
                KnowledgeDocument.updated_at < older_than,
            )
        )
        return list(result.scalars().all())

    async def replace_chunks(self, document: KnowledgeDocument, chunks: list[str], embeddings: list[list[float]]) -> None:
        await self.db.execute(
            text("DELETE FROM public.knowledge_chunks WHERE document_id = :document_id"),
            {"document_id": str(document.id)},
        )

        if chunks:
            rows = [
                {
                    "id": str(uuid4()),
                    "document_id": str(document.id),
                    "chatbot_id": str(document.chatbot_id),
                    "chunk_index": index,
                    "content": chunk,
                    # NOTE: word count, not a real tokenizer count. Fine as
                    # a rough size signal, but don't use it to budget an
                    # actual model context window.
                    "token_count": len(chunk.split()),
                    "embedding": self._vector_literal(embedding),
                }
                for index, (chunk, embedding) in enumerate(zip(chunks, embeddings))
            ]
            # One execute() with a list of params batches this as a single
            # round trip instead of one INSERT per chunk - matters once a
            # document produces 50-100+ chunks, and is gentler on pgbouncer
            # than issuing that many separate statements.
            await self.db.execute(
                text(
                    """
                    INSERT INTO public.knowledge_chunks (
                        id, document_id, chatbot_id, chunk_index, content, token_count, embedding
                    )
                    VALUES (
                        :id, :document_id, :chatbot_id, :chunk_index, :content, :token_count, CAST(:embedding AS vector(768))
                    )
                    """
                ),
                rows,
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
                    1 - (embedding <=> CAST(:embedding AS vector(768))) AS similarity
                FROM public.knowledge_chunks
                WHERE chatbot_id = :chatbot_id
                ORDER BY embedding <=> CAST(:embedding AS vector(768))
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

    async def search_chunks_by_keyword(self, chatbot_id: UUID, query: str, limit: int = 5) -> list[dict]:
        tokens = [token for token in re.findall(r"[a-z0-9]+", query.lower()) if len(token) > 2]
        if not tokens:
            return []

        result = await self.db.execute(
            text(
                """
                SELECT id, document_id, content
                FROM public.knowledge_chunks
                WHERE chatbot_id = :chatbot_id
                """
            ),
            {"chatbot_id": str(chatbot_id)},
        )

        rows = [dict(row._mapping) for row in result]
        if not rows:
            return []

        token_set = set(tokens)
        scored_rows = []
        for row in rows:
            content = (row["content"] or "").lower()
            overlap = sum(1 for token in token_set if token in content)
            if overlap:
                scored_rows.append({**row, "similarity": float(overlap)})

        scored_rows.sort(key=lambda item: item["similarity"], reverse=True)
        return scored_rows[:limit]

    def _vector_literal(self, embedding: list[float]) -> str:
        return f"[{','.join(f'{value:.8f}' for value in embedding)}]"