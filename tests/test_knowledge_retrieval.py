import asyncio
from uuid import uuid4

from app.knowledge.knowledgeRetrieval import KnowledgeRetriever


class FakeProvider:
    async def embed_texts(self, texts):
        return [[0.1, 0.2, 0.3]]

    async def generate_answer(self, question, chatbot_name, context, tone):
        return "NO_MATCH"

    async def generate_fallback_answer(self, chatbot_name, question, tone):
        return "I don't have that information in my knowledge base."


class FakeRepository:
    async def search_chunks(self, chatbot_id, embedding, limit=5):
        return [
            {
                "id": str(uuid4()),
                "document_id": str(uuid4()),
                "content": "The uploaded document says the refund window is 30 days.",
                "similarity": 0.92,
            }
        ]


class KeywordFallbackRepository:
    async def search_chunks(self, chatbot_id, embedding, limit=5):
        return []

    async def search_chunks_by_keyword(self, chatbot_id, query, limit=5):
        return [
            {
                "id": str(uuid4()),
                "document_id": str(uuid4()),
                "content": "Donaldson Sogolo is a software developer.",
                "similarity": 0.35,
            }
        ]


class RefusalProvider:
    async def embed_texts(self, texts):
        return [[0.1, 0.2, 0.3]]

    async def generate_answer(self, question, chatbot_name, context, tone):
        return "The information provided doesn't contain any details about where the person lives."

    async def generate_fallback_answer(self, chatbot_name, question, tone):
        return "I don't have that information in my knowledge base."


def test_retriever_falls_back_to_best_chunk_when_model_returns_no_match(monkeypatch):
    monkeypatch.setattr("app.knowledge.knowledgeRetrieval.get_ai_provider", lambda: FakeProvider())

    async def run_test():
        retriever = KnowledgeRetriever(FakeRepository())
        answer, matches = await retriever.answer_from_knowledge(
            chatbot_id=uuid4(),
            chatbot_name="Support Bot",
            question="How long is the refund window?",
            tone="friendly",
        )
        # Model returns NO_MATCH, so fallback generation is used instead of chunk
        assert answer == "I don't have that information in my knowledge base."
        assert len(matches) == 1

    asyncio.run(run_test())


def test_retriever_uses_keyword_fallback_when_vector_search_returns_no_matches(monkeypatch):
    monkeypatch.setattr("app.knowledge.knowledgeRetrieval.get_ai_provider", lambda: FakeProvider())

    async def run_test():
        retriever = KnowledgeRetriever(KeywordFallbackRepository())
        answer, matches = await retriever.answer_from_knowledge(
            chatbot_id=uuid4(),
            chatbot_name="Support Bot",
            question="Can you tell me who is Donaldson Sogolo please?",
            tone="friendly",
        )
        # Keyword fallback finds results, but FakeProvider returns NO_MATCH, so fallback generation is used
        assert answer == "I don't have that information in my knowledge base."
        assert len(matches) == 1

    asyncio.run(run_test())


def test_retriever_falls_back_when_model_gives_a_refusal_style_response(monkeypatch):
    monkeypatch.setattr("app.knowledge.knowledgeRetrieval.get_ai_provider", lambda: RefusalProvider())

    async def run_test():
        retriever = KnowledgeRetriever(FakeRepository())
        answer, matches = await retriever.answer_from_knowledge(
            chatbot_id=uuid4(),
            chatbot_name="Support Bot",
            question="Where does the person live?",
            tone="friendly",
        )
        # RefusalProvider returns refusal phrase, triggering fallback generation instead of chunk
        assert answer == "I don't have that information in my knowledge base."
        assert len(matches) == 1

    asyncio.run(run_test())


def test_retriever_rejects_short_queries():
    async def run_test():
        retriever = KnowledgeRetriever(FakeRepository())
        answer, matches = await retriever.answer_from_knowledge(
            chatbot_id=uuid4(),
            chatbot_name="Support Bot",
            question="Who?",
            tone="friendly",
        )
        # Short queries (< 5 words) should get a prompt for longer questions
        assert "more detailed question" in answer.lower()
        assert len(matches) == 0

    asyncio.run(run_test())
