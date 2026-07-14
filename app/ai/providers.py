from typing import Protocol

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalServiceError


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
                        "prompt": text,
                    },
                )

                if not response.is_success:
                    raise ExternalServiceError(
                        "Ollama embedding request failed."
                    )

                embeddings.append(
                    response.json()["embedding"]
                )

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

        prompt = f"""
You are {chatbot_name}.

Answer ONLY using the supplied business knowledge.

Tone:
{tone}

If the answer cannot be found, simply say you don't know.

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
        
        