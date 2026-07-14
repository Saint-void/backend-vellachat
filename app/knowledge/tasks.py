"""Background processing for knowledge documents."""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.ai.providers import get_ai_provider
from app.database.session import AsyncSessionLocal
from app.knowledge.chunking import TextChunker
from app.knowledge.extractors import KnowledgeTextExtractor
from app.knowledge.repository import KnowledgeRepository
from app.knowledge.storage import get_knowledge_storage

logger = logging.getLogger(__name__)


async def process_knowledge_document(document_id: UUID) -> None:
    async with AsyncSessionLocal() as db:
        repository = KnowledgeRepository(db)
        document = await repository.get_document_by_id(document_id)
        if document is None:
            logger.warning("process_knowledge_document called for missing document_id=%s", document_id)
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
            logger.exception("Knowledge processing failed for document_id=%s", document_id)
            await repository.mark_failed(document, str(exc))


async def sweep_stuck_documents(timeout_minutes: int = 20) -> int:
    """Fail documents that have been stuck in 'processing' too long.

    A BackgroundTasks job lives only as long as the process does - a
    Render restart or crash mid-processing kills it silently, leaving the
    document stuck forever with no error and no visibility. Run this on a
    schedule (cron / Render cron job) to catch and recover from that.
    Returns the number of documents it marked failed.
    """
    threshold = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)

    async with AsyncSessionLocal() as db:
        repository = KnowledgeRepository(db)
        stuck = await repository.list_stuck_processing(threshold)

        for document in stuck:
            logger.warning(
                "Marking stuck document %s as failed (processing > %d min)",
                document.id,
                timeout_minutes,
            )
            await repository.mark_failed(
                document,
                "Processing timed out or was interrupted, likely by a deploy or restart. Try reprocessing.",
            )

        return len(stuck)