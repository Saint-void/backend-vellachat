"""Knowledge retrieval for widget responses."""

import logging
from uuid import UUID

from app.ai.providers import get_ai_provider
from app.knowledge.repository import KnowledgeRepository
from app.knowledge.schemas import KnowledgeChunkMatch

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    # TODO: move to settings if these ever need to be tunable per chatbot.
    MIN_SIMILARITY = 0.18
    MAX_MATCHES = 4
    MAX_CONTEXT_CHUNKS = 3

    def __init__(self, repository: KnowledgeRepository):
        self.repository = repository

    async def answer_from_knowledge(
        self, chatbot_id: UUID, question: str, tone: str
    ) -> tuple[str | None, list[KnowledgeChunkMatch]]:
        provider = get_ai_provider()

        try:
            [query_embedding] = await provider.embed_texts([question])
        except Exception:
            logger.exception("Embedding failed for chatbot_id=%s", chatbot_id)
            return None, []

        try:
            rows = await self.repository.search_chunks(chatbot_id, query_embedding, limit=self.MAX_MATCHES)
        except Exception:
            logger.exception("Knowledge chunk search failed for chatbot_id=%s", chatbot_id)
            return None, []

        matches = [
            KnowledgeChunkMatch(
                id=row["id"],
                document_id=row["document_id"],
                content=row["content"],
                similarity=float(row["similarity"] or 0),
            )
            for row in rows
            if float(row["similarity"] or 0) >= self.MIN_SIMILARITY
        ]

        if not matches:
            return None, []

        try:
            answer = await provider.generate_answer(
                question, [match.content for match in matches[: self.MAX_CONTEXT_CHUNKS]], tone
            )
        except Exception:
            logger.exception("Answer generation failed for chatbot_id=%s", chatbot_id)
            # Still return matches - caller can fall back to a generic
            # response instead of hard-failing the whole request.
            return None, matches

        return answer or None, matches