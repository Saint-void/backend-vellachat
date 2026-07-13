"""Background processing for knowledge documents."""

from uuid import UUID

from app.ai.providers import get_ai_provider
from app.database.session import AsyncSessionLocal
from app.knowledge.chunking import TextChunker
from app.knowledge.extractors import KnowledgeTextExtractor
from app.knowledge.repository import KnowledgeRepository
from app.knowledge.storage import get_knowledge_storage


async def process_knowledge_document(document_id: UUID) -> None:
    async with AsyncSessionLocal() as db:
        repository = KnowledgeRepository(db)
        document = await repository.get_document_by_id(document_id)
        if document is None:
            return

        try:
            await repository.mark_processing(document)

            storage = get_knowledge_storage()
            if not document.storage_path:
                raise ValueError("Document has no stored source file")

            raw = await storage.read(document.storage_path)
            text = KnowledgeTextExtractor().extract(document.name, document.mime_type, raw)
            chunks = TextChunker().chunk(text)
            if not chunks:
                raise ValueError("No usable text was found in this document")

            embeddings = await get_ai_provider().embed_texts(chunks)
            await repository.replace_chunks(document, chunks, embeddings)
            await repository.mark_ready(document, len(text), len(chunks))
        except Exception as exc:
            await repository.mark_failed(document, str(exc))
