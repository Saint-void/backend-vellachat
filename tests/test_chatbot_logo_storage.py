from uuid import uuid4

import pytest

from app.chatbot.chatbotLogoStorage import ChatbotLogoStorage
from app.core.coreExceptions import ValidationError


@pytest.mark.asyncio
async def test_logo_storage_replaces_and_resolves_a_logo(tmp_path):
    storage = ChatbotLogoStorage(str(tmp_path), max_bytes=100)
    chatbot_id = uuid4()

    first = await storage.replace(chatbot_id, "image/png", b"\x89PNG\r\n\x1a\nfirst")
    second = await storage.replace(chatbot_id, "image/jpeg", b"\xff\xd8\xffsecond")

    assert first.name == "logo.png"
    assert not first.exists()
    assert second.name == "logo.jpg"
    assert await storage.resolve(chatbot_id) == second


@pytest.mark.asyncio
async def test_logo_storage_rejects_invalid_or_oversized_content(tmp_path):
    storage = ChatbotLogoStorage(str(tmp_path), max_bytes=8)
    chatbot_id = uuid4()

    with pytest.raises(ValidationError):
        await storage.replace(chatbot_id, "image/png", b"not an image")
    with pytest.raises(ValidationError):
        await storage.replace(chatbot_id, "image/png", b"\x89PNG\r\n\x1a\nlarge")
