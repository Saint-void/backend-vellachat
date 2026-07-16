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


_provider: AIProvider | None = None


def get_ai_provider() -> AIProvider:
    global _provider
    if _provider is None:
        if settings.AI_PROVIDER == "ollama":
            _provider = OllamaProvider(
                base_url=settings.OLLAMA_BASE_URL,
                embedding_model=settings.OLLAMA_EMBED_MODEL,
                chat_model=settings.OLLAMA_CHAT_MODEL,
            )
        else:
            raise ValueError(f"Unknown AI provider: {settings.AI_PROVIDER}")
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
        # It must emit NO_MATCH_SENTINEL exactly (nothing else on that line)
        # when the supplied context doesn't cover the question. Retrieval no
        # longer relies solely on a similarity-score cutoff to make that call
        # - see app/knowledge/retrieval.py.
        prompt = f"""
You are {chatbot_name}.

Answer ONLY using the supplied business knowledge below.

If, and only if, the business knowledge does not contain the answer,
respond with exactly this and nothing else: {NO_MATCH_SENTINEL}

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