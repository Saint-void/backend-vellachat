"""
Application entrypoint.

Builds the FastAPI app and wires up logging, middleware, exception
handlers, and routers. Nothing here does business logic -- if this
file is doing anything beyond assembling pieces defined elsewhere,
that logic is in the wrong place.
"""

from fastapi import FastAPI

from app.api.v1.health import router as health_router
from app.auth.authAuthrouter import router as auth_router
from app.chatbot.chatbotRouter import router as chatbot_router
from app.core.coreConfig import settings
from app.core.coreExceptions import (
    AppException,
    app_exception_handler,
    unhandled_exception_handler,
)
from app.core.coreLogging_config import configure_logging
from app.middleware.cors import add_cors_middleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.knowledge.knowledgeRouter import router as knowledge_router
from app.widget.widgetRouter import router as widget_router

configure_logging()

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
)

add_cors_middleware(app)
app.add_middleware(RequestLoggingMiddleware)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(health_router, prefix=settings.API_V1_PREFIX)
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(chatbot_router, prefix=settings.API_V1_PREFIX)
app.include_router(knowledge_router, prefix=settings.API_V1_PREFIX)
app.include_router(widget_router, prefix=settings.API_V1_PREFIX)

# Future routers mount the same way, one line each:
