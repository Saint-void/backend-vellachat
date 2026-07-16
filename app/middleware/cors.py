"""
CORS configuration.

Origins come from Settings, not hardcoded here -- every environment
(local, staging, prod) sets its own CORS_ORIGINS without touching this
file.

Note for later: this is CORS for the Next.js dashboard talking to its
own known origins. The public widget chat endpoint (module 6) gets
embedded on arbitrary customer domains that aren't known ahead of
time, so it will need its own per-request domain verification against
the chatbot's registered domain -- not a static CORS_ORIGINS list.
Don't try to solve that here.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.coreConfig import settings


def add_cors_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
