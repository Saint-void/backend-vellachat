"""Tests for widget conversation expiry."""

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.coreExceptions import ForbiddenError, NotFoundError, ValidationError
from app.widget.widgetSchemas import WidgetConversationRead
from app.widget.widgetService import WidgetService
from unittest.mock import MagicMock


class MockWidgetRepository:
    """Mock repository for testing widget service expiry logic."""
    
    def __init__(self):
        self.conversations = {}
        self.messages = {}
    
    async def get_chatbot(self, chatbot_id):
        """Return a mock chatbot."""
        class MockChatbot:
            id = chatbot_id
            greeting_message = "Hello!"
            status = "active"
            website_domain = "example.com"
        return MockChatbot()
    
    async def get_conversation(self, conversation_id, chatbot_id):
        """Return a stored conversation or None."""
        if conversation_id in self.conversations:
            return self.conversations[conversation_id]
        return None
    
    async def list_messages(self, conversation_id):
        """Return messages for a conversation."""
        return self.messages.get(conversation_id, [])
    
    def add_test_conversation(self, chatbot_id, conversation_id, status="open", updated_at=None):
        """Add a test conversation."""
        from app.widget.widgetModels import WidgetConversation
        
        if updated_at is None:
            updated_at = datetime.now(timezone.utc)
        
        now = datetime.now(timezone.utc)
        conv = WidgetConversation(
            id=conversation_id,
            chatbot_id=chatbot_id,
            site_origin="example.com",
            status=status,
            created_at=now,
            updated_at=updated_at,
        )
        self.conversations[conversation_id] = conv
        return conv


def test_read_conversation_allows_expired():
    """Test that expired conversations can still be read (for history)."""
    
    async def run_test():
        repo = MockWidgetRepository()
        service = WidgetService(repo)
        
        chatbot_id = uuid4()
        conversation_id = uuid4()
        
        # Add an expired conversation
        repo.add_test_conversation(
            chatbot_id,
            conversation_id,
            status="expired",
            updated_at=datetime.now(timezone.utc),
        )
        
        # Reading should succeed (for viewing history)
        result = await service.read_conversation(
            chatbot_id=chatbot_id,
            conversation_id=conversation_id,
            site_origin="example.com",
        )
        
        assert result.status == "expired"
        assert result.id == conversation_id
    
    asyncio.run(run_test())


def test_send_message_rejects_expired():
    """Test that sending a message to expired conversation raises ValidationError."""
    
    async def run_test():
        from app.widget.widgetSchemas import WidgetMessageCreate
        
        repo = MockWidgetRepository()
        service = WidgetService(repo)
        
        chatbot_id = uuid4()
        conversation_id = uuid4()
        
        # Add an expired conversation
        repo.add_test_conversation(
            chatbot_id,
            conversation_id,
            status="expired",
        )
        
        # Attempt to send should raise ValidationError
        try:
            await service.send_message(
                chatbot_id=chatbot_id,
                conversation_id=conversation_id,
                data=WidgetMessageCreate(
                    content="Hello",
                    site_origin="example.com",
                ),
            )
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "expired" in str(e).lower()
    
    asyncio.run(run_test())


def test_localhost_origin_is_allowed_for_dev_widget_requests():
    """Allow localhost-based widget embeds to work during local development."""

    async def run_test():
        repo = LocalhostWidgetRepository()
        service = WidgetService(repo)

        chatbot_id = uuid4()
        fake_request = MagicMock()
        fake_request.url.scheme = "http"
        fake_request.url.netloc = "localhost:8000"
        result = await service.get_config(chatbot_id, "http://localhost:3001", fake_request)
        assert result.chatbot_id == chatbot_id

    asyncio.run(run_test())


class LocalhostWidgetRepository(MockWidgetRepository):
    async def get_chatbot(self, chatbot_id):
        class MockChatbot:
            id = chatbot_id
            greeting_message = "Hello!"
            status = "active"
            website_domain = "example.com"
            name = "Demo"
            business_name = "Demo"
            industry = None
            support_goal = None
            brand_color = ""
            logo_url = ""
            widget_settings = {}
            tone = "friendly"

        return MockChatbot()
