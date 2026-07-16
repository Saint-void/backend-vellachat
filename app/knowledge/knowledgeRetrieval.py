"""Knowledge retrieval for widget responses."""

import logging
from uuid import UUID

from app.ai.aiProviders import NO_MATCH_SENTINEL, get_ai_provider
from app.knowledge.knowledgeRepository import KnowledgeRepository
from app.knowledge.knowledgeSchemas import KnowledgeChunkMatch

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    # TODO: move to settings if these ever need to be tunable per chatbot.
    #
    # MIN_SIMILARITY is now just a noise filter - it exists to avoid paying
    # for an ~180s Ollama generation call on chunks that are pure garbage
    # (cosine near zero), NOT to decide whether the answer is "good enough".
    # That decision now belongs to the model via NO_MATCH_SENTINEL below.
    # Retune this once you've watched real top_similarity values in prod -
    # see the logger.info call in answer_from_knowledge.
    MIN_SIMILARITY = 0.20
    MAX_MATCHES = 4
    MAX_CONTEXT_CHUNKS = 3

    def __init__(self, repository: KnowledgeRepository):
        self.repository = repository

    async def answer_from_knowledge(
        self, chatbot_id: UUID, chatbot_name: str, question: str, tone: str
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

        # Log every search regardless of outcome - this is what you were
        # missing when you had to reverse-engineer the gate from raw SQL
        # logs. Grep this line instead, next time.
        top_similarity = max((float(row["similarity"] or 0) for row in rows), default=None)
        logger.info(
            "knowledge_search chatbot_id=%s question_len=%d top_similarity=%s row_count=%d",
            chatbot_id,
            len(question),
            top_similarity,
            len(rows),
        )

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
                question, chatbot_name, [match.content for match in matches[: self.MAX_CONTEXT_CHUNKS]], tone
            )
            logger.info("generation_raw chatbot_id=%s raw_answer=%r", chatbot_id, answer)
        except Exception:
            logger.exception("Answer generation failed for chatbot_id=%s", chatbot_id)
            # Still return matches - caller can fall back to a generic
            # response instead of hard-failing the whole request.
            return None, matches

        answer = (answer or "").strip()

        # The model, not a similarity score, gets the final say on whether
        # it actually had enough to answer. Normalize casing/whitespace
        # since small local models aren't perfectly reliable about exact
        # string output - if this still drifts in practice, switch to
        # NO_MATCH_SENTINEL in answer.upper() instead of equality.
        if not answer or answer.upper() == NO_MATCH_SENTINEL:
            logger.info("generation_no_match chatbot_id=%s", chatbot_id)
            return None, matches

        return answer, matches