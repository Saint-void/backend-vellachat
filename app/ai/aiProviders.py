from typing import Protocol

import httpx

from app.core.coreConfig import settings
from app.core.coreExceptions import ExternalServiceError

NO_MATCH_SENTINEL = "NO_MATCH"


class AIProvider(Protocol):
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...

    async def generate_answer(
        self,
        question: str,
        chatbot_name: str,
        context: list[str],
        tone: str,
    ) -> str:
        ...

    async def generate_fallback_answer(
        self,
        chatbot_name: str,
        question: str,
        tone: str,
    ) -> str:
        ...


_provider: AIProvider | None = None


def get_ai_provider() -> AIProvider:
    global _provider
    if _provider is None:
        _provider = OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            embedding_model=settings.OLLAMA_EMBED_MODEL,
            chat_model=settings.OLLAMA_CHAT_MODEL,
        )
    return _provider


class OllamaProvider:
    """
    Uses the local Ollama server.

    Chat:
        qwen3:4b
        gemma3:4b
        llama3.2

    Embeddings:
        nomic-embed-text

    Runs entirely on Apple Silicon using Metal.
    """

    def __init__(
        self,
        base_url: str,
        embedding_model: str,
        chat_model: str,
    ):
        self.base_url = base_url.rstrip("/")
        self.embedding_model = embedding_model
        self.chat_model = chat_model

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings = []

        async with httpx.AsyncClient(timeout=60) as client:

            for text in texts:

                response = await client.post(
                    f"{self.base_url}/api/embed",
                    json={
                        "model": self.embedding_model,
                        "input": text,
                    },
                )

                if not response.is_success:
                    raise ExternalServiceError(
                        "Ollama embedding request failed."
                    )

                data = response.json()
                embeddings.append(data["embeddings"][0])

        return embeddings

    async def generate_answer(
        self,
        question: str,
        chatbot_name: str,
        context: list[str],
        tone: str,
    ) -> str:

        if not context:
            return ""

        # NOTE: the model itself now owns the "can I answer this" decision.
        # It should answer directly from the supplied knowledge whenever it
        # can. Only use the sentinel when the retrieved context truly does
        # not contain the answer.
        prompt = f"""
You are {chatbot_name}.

Answer the user's question using ONLY the business knowledge below.

- If the business knowledge contains the answer, provide the answer directly and concisely.
- If the business knowledge only partially contains the answer, give the best answer you can from the supplied knowledge.
- Do not return placeholders unless the knowledge contains no relevant information at all.
- Never return {NO_MATCH_SENTINEL} if you can provide a useful answer from the knowledge.

Tone:
{tone}

Business Knowledge
------------------

{chr(10).join(context)}

Question
--------

{question}
"""

        async with httpx.AsyncClient(timeout=180) as client:

            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.chat_model,
                    "prompt": prompt,
                    "stream": False,
                },
            )

            if not response.is_success:
                raise ExternalServiceError(
                    "Ollama generation failed."
                )

            return response.json()["response"].strip()

    async def generate_fallback_answer(
        self,
        chatbot_name: str,
        question: str,
        tone: str,
    ) -> str:
        """Generate a response when no relevant knowledge is found in the knowledge base."""
        prompt = f"""You are {chatbot_name}.

The user asked: "{question}"

IMPORTANT: We do NOT have information about this topic in our knowledge base.

Do NOT try to answer this question from your general knowledge.
Do NOT provide information about topics outside our knowledge base.

Instead, respond in a {tone} way that clearly states you don't have information about this topic. 

Be direct: "I don't have information about that in my knowledge base." or similar.

You can briefly mention what topics you CAN help with if appropriate, but do NOT provide information about the user's question.
"""

        async with httpx.AsyncClient(timeout=180) as client:

            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.chat_model,
                    "prompt": prompt,
                    "stream": False,
                },
            )

            if not response.is_success:
                raise ExternalServiceError(
                    "Ollama fallback generation failed."
                )

            return response.json()["response"].strip()