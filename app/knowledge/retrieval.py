"""Knowledge retrieval for widget responses."""

from uuid import UUID

from app.ai.providers import get_ai_provider
from app.knowledge.repository import KnowledgeRepository
from app.knowledge.schemas import KnowledgeChunkMatch


class KnowledgeRetriever:
    def __init__(self, repository: KnowledgeRepository):
        self.repository = repository

    async def answer_from_knowledge(self, chatbot_id: UUID, question: str, tone: str) -> tuple[str | None, list[KnowledgeChunkMatch]]:
        provider = get_ai_provider()
        [query_embedding] = await provider.embed_texts([question])
        rows = await self.repository.search_chunks(chatbot_id, query_embedding, limit=4)
        matches = [
            KnowledgeChunkMatch(
                id=row["id"],
                document_id=row["document_id"],
                content=row["content"],
                similarity=float(row["similarity"] or 0),
            )
            for row in rows
            if float(row["similarity"] or 0) >= 0.18
        ]

        if not matches:
            return None, []

        answer = await provider.generate_answer(question, [match.content for match in matches[:3]], tone)
        return answer or None, matches
