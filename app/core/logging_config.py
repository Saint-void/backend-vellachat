"""
Structured logging setup.

Emits JSON in production (so Railway/Render's log aggregation can
parse fields like level and logger name) and plain, readable text in
development. Called once from main.py before the app starts handling
requests.
"""

import json
import logging
import sys

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)

    handler = logging.StreamHandler(sys.stdout)
    if settings.ENVIRONMENT == "production":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
        )

    root.handlers = [handler]

    # Quiet down noisy third-party loggers so app logs aren't drowned out.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
