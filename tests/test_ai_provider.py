import asyncio

import pytest

from app.ai.aiProviders import OllamaProvider
from app.core.config import settings


@pytest.mark.skipif(
    settings.AI_PROVIDER != "ollama",
    reason="requires a running Ollama server",
)
def test_ollama_provider_returns_answer_from_context():
    provider = OllamaProvider(
        base_url=settings.OLLAMA_BASE_URL,
        embedding_model=settings.OLLAMA_EMBED_MODEL,
        chat_model=settings.OLLAMA_CHAT_MODEL,
    )

    answer = asyncio.run(
        provider.generate_answer(
            "What software skills are mentioned?",
            "TestBot",
            ["The document mentions React, Node.js, Python, SQL, AWS, and Git."],
            "friendly",
        )
    )

    assert len(answer) > 0
