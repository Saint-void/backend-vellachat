import asyncio

from app.ai.providers import LocalAIProvider


def test_local_provider_returns_concise_answer_from_context():
    provider = LocalAIProvider(dimensions=32)

    answer = asyncio.run(
        provider.generate_answer(
            "What software skills are mentioned?",
            ["The document mentions React, Node.js, Python, SQL, AWS, and Git."],
            "friendly",
        )
    )

    assert "React" in answer
    assert "Python" in answer
    assert "The document mentions" not in answer
    assert answer.startswith("Based on the uploaded knowledge")
