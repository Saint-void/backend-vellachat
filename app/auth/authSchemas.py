"""Request/response shapes for the auth/profile endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str | None
    last_name: str | None
    created_at: datetime


class ProfileUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None


class SignupRequest(BaseModel):
    email: str
    password: str
    first_name: str | None = None
    last_name: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class OAuthAuthorizeUrlRead(BaseModel):
    url: str


class AuthUserRead(BaseModel):
    id: UUID
    email: str | None = None


class AuthSessionRead(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str | None = None
    expires_in: int | None = None
    user: AuthUserRead | None = None
    message: str | None = None
