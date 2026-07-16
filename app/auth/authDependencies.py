"""
JWT verification against Supabase's JWKS endpoint.

Supabase signs session JWTs asymmetrically (ES256, occasionally RSA)
by default for any project created after mid-2025, publishing the
public verification keys at a JWKS endpoint. That means verification
happens locally, on every request, using PyJWKClient to fetch and
cache those public keys -- no shared secret sits in an env var, and
we never call out to Supabase's Auth server to check a token.

If this project is on the older symmetric (HS256 + shared secret)
system instead -- check Project Settings -> JWT in the Supabase
dashboard -- the JWKS endpoint returns no keys and this will fail
closed (every request unauthorized, never open). Swapping in a
shared-secret HS256 check is a smaller change than this file; ask if
that turns out to be the case.
"""

from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Header
from jwt import PyJWKClient

from app.core.coreConfig import settings
from app.core.coreExceptions import UnauthorizedError

# lifespan=600 matches the ~10 minute edge cache Supabase itself puts
# in front of the JWKS endpoint -- no point re-fetching more often
# than the source can actually change.
_jwks_client = PyJWKClient(
    f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json",
    lifespan=600,
)


@dataclass
class CurrentUser:
    id: UUID
    email: str | None


def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    """
    FastAPI dependency for any protected route.

    Usage: `current_user: CurrentUser = Depends(get_current_user)`.
    Raises UnauthorizedError (-> 401) for anything wrong with the
    token -- missing, malformed, expired, or badly signed all look the
    same to the caller. Never reveals which.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        raise UnauthorizedError("Missing or malformed Authorization header")

    token = authorization.removeprefix("Bearer ").strip()

    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc

    try:
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Invalid or expired token") from exc

    return CurrentUser(id=user_id, email=payload.get("email"))
