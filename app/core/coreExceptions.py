"""
Application-wide exception hierarchy and handlers.

Services and repositories raise these instead of raising HTTPException
directly -- that would leak HTTP concerns into business logic and
couple every module to FastAPI. The handlers registered in main.py
convert them to the right HTTP response at the edge, once, in one
place, instead of every route hand-rolling its own try/except.
"""

import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger("vella")


class AppException(Exception):
    """Base for every domain exception in the application."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "internal_error"

    def __init__(self, message: str = "An unexpected error occurred"):
        self.message = message
        super().__init__(message)


class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"


class ValidationError(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    error_code = "validation_error"


class UnauthorizedError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "unauthorized"


class ForbiddenError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "forbidden"


class ConflictError(AppException):
    status_code = status.HTTP_409_CONFLICT
    error_code = "conflict"


class ExternalServiceError(AppException):
    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "external_service_error"


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Converts any AppException subclass into a consistent JSON error shape."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error_code, "message": exc.message},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Last-resort handler for anything that isn't an AppException.

    Logs the full exception server-side (with traceback) but returns a
    generic message to the caller -- never leak internals like stack
    traces or raw DB errors across the API boundary.
    """
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "internal_error", "message": "An unexpected error occurred"},
    )
