"""Knowledge retrieval for widget responses."""

import logging
from uuid import UUID

from app.ai.aiProviders import NO_MATCH_SENTINEL, get_ai_provider
from app.knowledge.knowledgeRepository import KnowledgeRepository
from app.knowledge.knowledgeSchemas import KnowledgeChunkMatch

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    MAX_MATCHES = 4
    MAX_CONTEXT_CHUNKS = 3
    SIMILARITY_THRESHOLD = 0.5  # If best match is below this, no relevant knowledge found


    def __init__(self, repository: KnowledgeRepository):
        self.repository = repository

    async def answer_from_knowledge(
        self, chatbot_id: UUID, chatbot_name: str, question: str, tone: str
    ) -> tuple[str | None, list[KnowledgeChunkMatch]]:
        provider = get_ai_provider()

        # Check if question is substantial enough (at least 5 letters)
        clean_question = question.strip()
        letter_count = len([c for c in clean_question if c.isalpha()])
        if letter_count < 5:
            logger.info(
                "generation_query_too_short chatbot_id=%s letter_count=%d",
                chatbot_id,
                letter_count,
            )
            return (
                "Please provide a more detailed question so I can better assist you. Try to ask in at least 5 letters.",
                [],
            )

        try:
            [query_embedding] = await provider.embed_texts([clean_question])
        except Exception:
            logger.exception("Embedding failed for chatbot_id=%s", chatbot_id)
            return None, []

        try:
            rows = await self.repository.search_chunks(chatbot_id, query_embedding, limit=self.MAX_MATCHES)
        except Exception:
            logger.exception("Knowledge chunk search failed for chatbot_id=%s", chatbot_id)
            return None, []

        # Track whether we used keyword fallback
        used_keyword_fallback = False
        if not rows and hasattr(self.repository, "search_chunks_by_keyword"):
            try:
                rows = await self.repository.search_chunks_by_keyword(chatbot_id, question, limit=self.MAX_MATCHES)
                used_keyword_fallback = True
            except Exception:
                logger.exception("Keyword knowledge fallback failed for chatbot_id=%s", chatbot_id)
                rows = []

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
        ]

        # Check if we have meaningful knowledge
        # Only apply threshold to vector search results; keyword results always proceed to answer generation
        best_similarity = max((match.similarity for match in matches), default=0)
        if not matches or (not used_keyword_fallback and best_similarity < self.SIMILARITY_THRESHOLD):
            logger.info(
                "generation_no_knowledge chatbot_id=%s best_similarity=%s used_keyword=%s",
                chatbot_id,
                best_similarity,
                used_keyword_fallback,
            )
            try:
                fallback_answer = await provider.generate_fallback_answer(
                    chatbot_name, question, tone
                )
                return fallback_answer, matches
            except Exception:
                logger.exception("Fallback generation failed for chatbot_id=%s", chatbot_id)
                return None, matches

        answer = None
        for attempt in range(2):
            try:
                answer = await provider.generate_answer(
                    question, chatbot_name, [match.content for match in matches[: self.MAX_CONTEXT_CHUNKS]], tone
                )
                logger.info("generation_raw chatbot_id=%s attempt=%d raw_answer=%r", chatbot_id, attempt + 1, answer)
            except Exception:
                logger.exception("Answer generation failed for chatbot_id=%s", chatbot_id)
                # Fall back to fallback generation instead of showing chunk
                try:
                    fallback_answer = await provider.generate_fallback_answer(
                        chatbot_name, question, tone
                    )
                    return fallback_answer, matches
                except Exception:
                    logger.exception("Fallback generation failed for chatbot_id=%s", chatbot_id)
                    return None, matches

            answer = (answer or "").strip()
            
            # Check if the answer is a refusal/no-answer response:
            # 1. Explicit NO_MATCH sentinel
            # 2. Phrases indicating the model couldn't find an answer
            if not self._is_valid_answer(answer):
                if attempt == 0:
                    logger.info("generation_retry chatbot_id=%s", chatbot_id)
                    continue
                else:
                    logger.info("generation_no_match chatbot_id=%s", chatbot_id)
                    # Model refused even with context - use fallback generation instead of chunk
                    try:
                        fallback_answer = await provider.generate_fallback_answer(
                            chatbot_name, question, tone
                        )
                        return fallback_answer, matches
                    except Exception:
                        logger.exception("Fallback generation failed after model refusal for chatbot_id=%s", chatbot_id)
                        return None, matches
            
            return answer, matches

        return None, matches

    def _fallback_answer_from_matches(self, matches: list[KnowledgeChunkMatch]) -> str | None:
        if not matches:
            return None

        best_match = max(matches, key=lambda match: match.similarity)
        content = (best_match.content or "").strip()
        if not content:
            return None

        return content

    def _is_valid_answer(self, answer: str) -> bool:
        """
        Check if the answer is a valid response or a refusal/no-answer signal.
        
        Returns False if:
        - Answer is empty
        - Starts with NO_MATCH sentinel
        - Contains common refusal phrases indicating no answer was found
        """
        if not answer:
            return False
        
        upper = answer.upper()
        if upper.startswith(NO_MATCH_SENTINEL):
            return False
        
        # Detect common refusal patterns from local models
        refusal_patterns = [
            "DOESN'T CONTAIN",
            "DOES NOT CONTAIN",
            "NO INFORMATION",
            "NOT PROVIDED",
            "NOT FOUND",
            "CANNOT FIND",
            "NO DETAILS",
            "NO ANSWER",
            "DON'T HAVE",
            "I DON'T HAVE",
            "UNABLE TO",
        ]
        
        for pattern in refusal_patterns:
            if pattern in upper:
                return False
        
        return True