"""Business logic for the public widget runtime."""

from urllib.parse import urlparse
from uuid import UUID

from app.chatbot.chatbotModels import Chatbot
from app.core.coreExceptions import ForbiddenError, NotFoundError, ValidationError
from app.knowledge.knowledgeRepository import KnowledgeRepository
from app.knowledge.knowledgeRetrieval import KnowledgeRetriever
from app.widget.widgetModels import WidgetConversation
from app.widget.widgetRepository import WidgetRepository
from app.widget.widgetSchemas import (
    WidgetConfigRead,
    WidgetConversationCreate,
    WidgetConversationRead,
    WidgetMessageCreate,
    WidgetMessageRead,
    WidgetSendMessageRead,
)


class WidgetService:
    def __init__(self, repository: WidgetRepository):
        self.repository = repository

    async def get_config(self, chatbot_id: UUID, site_origin: str) -> WidgetConfigRead:
        chatbot = await self._get_chatbot(chatbot_id)
        self._validate_origin(chatbot, site_origin)
        return self._config_from_chatbot(chatbot)

    async def create_conversation(self, chatbot_id: UUID, data: WidgetConversationCreate) -> WidgetConversationRead:
        chatbot = await self._get_chatbot(chatbot_id)
        self._validate_origin(chatbot, data.site_origin)
        conversation = await self.repository.create_conversation(chatbot.id, data.site_origin, data.visitor_id)
        await self.repository.create_message(conversation, "assistant", chatbot.greeting_message)
        return await self._load_conversation(conversation)

    async def read_conversation(
        self,
        chatbot_id: UUID,
        conversation_id: UUID,
        site_origin: str,
        visitor_id: str | None = None,
    ) -> WidgetConversationRead:
        chatbot = await self._get_chatbot(chatbot_id)
        self._validate_origin(chatbot, site_origin)
        conversation = await self.repository.get_conversation(conversation_id, chatbot.id)
        if conversation is None:
            raise NotFoundError("Conversation not found")
        self._validate_conversation_access(conversation, site_origin, visitor_id)
        return await self._load_conversation(conversation)

    async def send_message(
        self,
        chatbot_id: UUID,
        conversation_id: UUID,
        data: WidgetMessageCreate,
    ) -> WidgetSendMessageRead:
        chatbot = await self._get_chatbot(chatbot_id)
        self._validate_origin(chatbot, data.site_origin)

        conversation = await self.repository.get_conversation(conversation_id, chatbot.id)
        if conversation is None:
            raise NotFoundError("Conversation not found")
        if conversation.status != "open":
            raise ValidationError("This conversation has expired. Start a new one by refreshing.")
        self._validate_conversation_access(conversation, data.site_origin, data.visitor_id)

        content = data.content.strip()
        if not content:
            raise ValidationError("Message cannot be empty")

        visitor_message = await self.repository.create_message(conversation, "visitor", content)
        reply_text = await self._build_reply(chatbot, content)
        assistant_message = await self.repository.create_message(conversation, "assistant", reply_text)

        return WidgetSendMessageRead(
            conversation_id=conversation.id,
            visitor_message=WidgetMessageRead.model_validate(visitor_message),
            assistant_message=WidgetMessageRead.model_validate(assistant_message),
        )

    async def close_conversation(
        self,
        chatbot_id: UUID,
        conversation_id: UUID,
        site_origin: str,
        visitor_id: str | None = None,
    ) -> WidgetConversationRead:
        """Explicitly close a conversation from the client side."""
        chatbot = await self._get_chatbot(chatbot_id)
        self._validate_origin(chatbot, site_origin)
        conversation = await self.repository.get_conversation(conversation_id, chatbot.id)
        if conversation is None:
            raise NotFoundError("Conversation not found")
        self._validate_conversation_access(conversation, site_origin, visitor_id)
        await self.repository.close_conversation(conversation)
        return await self._load_conversation(conversation)

    async def _get_chatbot(self, chatbot_id: UUID) -> Chatbot:
        chatbot = await self.repository.get_chatbot(chatbot_id)
        if chatbot is None:
            raise NotFoundError("Chatbot not found")
        return chatbot

    async def _load_conversation(self, conversation: WidgetConversation) -> WidgetConversationRead:
        messages = await self.repository.list_messages(conversation.id)

        conversation_data = {
            column.name: getattr(conversation, column.name)
            for column in conversation.__table__.columns
        }
        conversation_data["messages"] = [
            WidgetMessageRead.model_validate(message) for message in messages
        ]

        return WidgetConversationRead.model_validate(conversation_data)

    async def _build_reply(self, chatbot: Chatbot, content: str) -> str:
        """
        User -> embedding search -> relevant context -> AI -> response.

        No FAQ pre-match, no low-signal short-circuit: every message goes
        to KnowledgeRetriever. The only remaining fallback covers the two
        cases that flow can't itself resolve -- a knowledge base with zero
        chunks, or the Ollama call failing outright.
        """
        knowledge_answer, _matches = await KnowledgeRetriever(
            KnowledgeRepository(self.repository.db)
        ).answer_from_knowledge(chatbot.id, chatbot.name, content, chatbot.tone)

        if knowledge_answer:
            return knowledge_answer.strip()

        return self._fallback_reply(chatbot)

    def _fallback_reply(self, chatbot: Chatbot) -> str:
        if chatbot.handoff_email:
            return f"Thanks for reaching out. I don't have an answer for that yet, but our team can help at {chatbot.handoff_email}."
        return "Thanks for reaching out. I don't have an answer for that yet, but I'll pass it along to the team."

    def _config_from_chatbot(self, chatbot: Chatbot) -> WidgetConfigRead:
        suggestions = self._suggested_questions(chatbot)
        return WidgetConfigRead(
            chatbot_id=chatbot.id,
            name=chatbot.name,
            business_name=chatbot.business_name,
            industry=chatbot.industry,
            support_goal=chatbot.support_goal,
            greeting_message=chatbot.greeting_message,
            brand_color=chatbot.brand_color,
            logo_url=chatbot.logo_url,
            tone=chatbot.tone,
            suggested_questions=suggestions,
        )

    def _suggested_questions(self, chatbot: Chatbot) -> list[str]:
        questions = [
            "What are your business hours?",
            "How do I get help with my order?",
            "Can I speak to a person?",
        ]
        if chatbot.support_goal:
            questions.insert(0, chatbot.support_goal.strip())
        return questions[:3]

    def _validate_origin(self, chatbot: Chatbot, site_origin: str) -> None:
        if chatbot.status != "active":
            raise ForbiddenError("This chatbot is not active")

        if not chatbot.website_domain:
            raise ValidationError("Set a website domain before publishing this widget")

        if not self._origin_matches(site_origin, chatbot.website_domain):
            raise ForbiddenError("This widget is not allowed on that domain")

    def _validate_conversation_access(
        self,
        conversation: WidgetConversation,
        site_origin: str,
        visitor_id: str | None,
    ) -> None:
        if self._canonical_origin(conversation.site_origin) != self._canonical_origin(site_origin):
            raise ForbiddenError("Conversation does not belong to this site")

        if conversation.visitor_id and conversation.visitor_id != visitor_id:
            raise ForbiddenError("Conversation does not belong to this visitor")

    def _origin_matches(self, site_origin: str, website_domain: str) -> bool:
        site_origin = site_origin.strip()
        website_domain = website_domain.strip().lower().rstrip("/")

        site_parsed = urlparse(site_origin if "://" in site_origin else f"https://{site_origin}")
        site_scheme = site_parsed.scheme or "https"
        site_host = (site_parsed.hostname or "").lower()
        site_port = site_parsed.port or self._default_port(site_scheme)

        if self._is_local_development_origin(site_origin):
            return True

        if "://" in website_domain:
            allowed = urlparse(website_domain)
            allowed_scheme = allowed.scheme or "https"
            allowed_host = (allowed.hostname or "").lower()
            allowed_port = allowed.port or self._default_port(allowed_scheme)
            return (
                site_scheme == allowed_scheme
                and site_host == allowed_host
                and site_port == allowed_port
            )

        allowed = urlparse(f"https://{website_domain}")
        allowed_host = (allowed.hostname or "").lower()
        allowed_port = allowed.port

        if allowed_port is not None:
            return site_host == allowed_host and site_port == allowed_port

        return site_host == allowed_host or site_host.endswith(f".{allowed_host}")

    def _is_local_development_origin(self, site_origin: str) -> bool:
        try:
            parsed = urlparse(site_origin if "://" in site_origin else f"https://{site_origin}")
        except Exception:
            return False
        host = (parsed.hostname or "").lower()
        return host in {"localhost", "127.0.0.1", "::1"}

    def _canonical_origin(self, value: str) -> str:
        parsed = urlparse(value.strip() if "://" in value else f"https://{value.strip()}")
        scheme = parsed.scheme or "https"
        host = (parsed.hostname or "").lower()
        port = parsed.port or self._default_port(scheme)
        return f"{scheme}://{host}:{port}" if port else f"{scheme}://{host}"

    def _default_port(self, scheme: str) -> int | None:
        if scheme == "http":
            return 80
        if scheme == "https":
            return 443
        return None