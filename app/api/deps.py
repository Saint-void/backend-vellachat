"""
Shared FastAPI dependencies.

Anything more than one route module needs lives here, so routers
import from a single place instead of reaching into
app.database.session or app.auth internals directly -- that
indirection is what keeps auth swappable later without touching every
other module.
"""

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.session import get_db

__all__ = ["get_db", "get_current_user", "CurrentUser"]
