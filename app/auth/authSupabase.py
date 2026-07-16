"""Small server-side client for Supabase Auth."""

from typing import Any
from urllib.parse import urlencode

import httpx

from app.auth.authSchemas import AuthSessionRead, AuthUserRead, LoginRequest, SignupRequest
from app.core.coreConfig import settings
from app.core.coreExceptions import ExternalServiceError, UnauthorizedError, ValidationError


class SupabaseAuthClient:
    def __init__(self) -> None:
        self.base_url = f"{settings.SUPABASE_URL}/auth/v1"
        self.headers = {
            "apikey": settings.SUPABASE_PUBLISHABLE_KEY,
            "Content-Type": "application/json",
        }

    async def sign_up(self, data: SignupRequest) -> AuthSessionRead:
        payload = {
            "email": data.email,
            "password": data.password,
            "data": {
                "first_name": data.first_name,
                "last_name": data.last_name,
            },
        }
        body = await self._request("POST", "/signup", json=payload)
        session = self._to_session(body)

        if session.access_token is None:
            session.message = "Check your email to verify your account."

        return session

    async def sign_in_with_password(self, data: LoginRequest) -> AuthSessionRead:
        body = await self._request(
            "POST",
            "/token",
            params={"grant_type": "password"},
            json={"email": data.email, "password": data.password},
        )
        return self._to_session(body)

    def oauth_authorize_url(self, provider: str, redirect_to: str) -> str:
        if provider not in {"google", "github"}:
            raise ValidationError("Unsupported OAuth provider")

        query = urlencode({"provider": provider, "redirect_to": redirect_to})
        return f"{self.base_url}/authorize?{query}"

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=15) as client:
                response = await client.request(method, path, headers=self.headers, **kwargs)
        except httpx.HTTPError as exc:
            raise ExternalServiceError("Could not reach Supabase Auth") from exc

        if response.is_success:
            return response.json()

        message = self._error_message(response)
        if response.status_code in {400, 401}:
            raise UnauthorizedError(message)
        if response.status_code == 422:
            raise ValidationError(message)

        raise ExternalServiceError(message)

    @staticmethod
    def _error_message(response: httpx.Response) -> str:
        fallback = "Authentication failed"
        try:
            body = response.json()
        except ValueError:
            return fallback

        return (
            body.get("msg")
            or body.get("message")
            or body.get("error_description")
            or body.get("error")
            or fallback
        )

    @staticmethod
    def _to_session(body: dict[str, Any]) -> AuthSessionRead:
        user = body.get("user")
        return AuthSessionRead(
            access_token=body.get("access_token"),
            refresh_token=body.get("refresh_token"),
            token_type=body.get("token_type"),
            expires_in=body.get("expires_in"),
            user=AuthUserRead(id=user["id"], email=user.get("email")) if user else None,
        )


supabase_auth = SupabaseAuthClient()
