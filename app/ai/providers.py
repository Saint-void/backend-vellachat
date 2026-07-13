"""AI provider contracts and implementations."""

import hashlib
import math
import re
from typing import Protocol

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalServiceError, ValidationError


class AIProvider(Protocol):
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""

    async def generate_answer(self, question: str, context: list[str], tone: str) -> str:
        """Generate an answer from retrieved context."""


class LocalAIProvider:
    """
    Deterministic local provider for development.

    It is not semantically smart like OpenAI embeddings, but it lets
    the whole knowledge pipeline run without network access or secrets.
    """

    def __init__(self, dimensions: int):
        self.dimensions = dimensions

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    async def generate_answer(self, question: str, context: list[str], tone: str) -> str:
        if not context:
            return ""

        joined = "\n\n".join(context)
        if len(joined) > 1200:
            joined = f"{joined[:1200].rsplit(' ', 1)[0]}..."

        return f"Based on the uploaded knowledge, here is what I found:\n\n{joined}"

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = re.findall(r"[a-z0-9]+", text.lower())

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


class OpenAIProvider:
    def __init__(self, api_key: str, embedding_model: str, chat_model: str):
        self.api_key = api_key
        self.embedding_model = embedding_model
        self.chat_model = chat_model

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.embedding_model, "input": texts},
                )
        except httpx.HTTPError as exc:
            raise ExternalServiceError("Could not reach embedding provider") from exc

        if not response.is_success:
            raise ExternalServiceError("Embedding provider rejected the request")

        body = response.json()
        return [item["embedding"] for item in body["data"]]

    async def generate_answer(self, question: str, context: list[str], tone: str) -> str:
        if not context:
            return ""

        try:
            async with httpx.AsyncClient(timeout=45) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.chat_model,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "Answer customer questions using only the provided business knowledge. "
                                    f"Use a {tone} tone. If the context is insufficient, say so briefly."
                                ),
                            },
                            {"role": "user", "content": f"Question:\n{question}\n\nKnowledge:\n{chr(10).join(context)}"},
                        ],
                    },
                )
        except httpx.HTTPError as exc:
            raise ExternalServiceError("Could not reach answer provider") from exc

        if not response.is_success:
            raise ExternalServiceError("Answer provider rejected the request")

        return response.json()["choices"][0]["message"]["content"].strip()


def get_ai_provider() -> AIProvider:
    if settings.AI_PROVIDER == "local":
        return LocalAIProvider(settings.AI_EMBEDDING_DIMENSIONS)

    if not settings.OPENAI_API_KEY:
        raise ValidationError("OPENAI_API_KEY is required when AI_PROVIDER=openai")

    return OpenAIProvider(
        settings.OPENAI_API_KEY,
        settings.OPENAI_EMBEDDING_MODEL,
        settings.OPENAI_CHAT_MODEL,
    )
