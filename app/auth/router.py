"""Auth routes."""

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.auth.dependencies import CurrentUser, get_current_user
from app.auth.repository import ProfileRepository
from app.auth.schemas import AuthSessionRead, LoginRequest, ProfileRead, ProfileUpdate, SignupRequest
from app.auth.service import ProfileService
from app.auth.supabase import supabase_auth

router = APIRouter(prefix="/auth", tags=["auth"])


def get_profile_service(db: AsyncSession = Depends(get_db)) -> ProfileService:
    return ProfileService(ProfileRepository(db))


@router.post("/signup", response_model=AuthSessionRead, status_code=status.HTTP_201_CREATED)
async def signup(data: SignupRequest):
    return await supabase_auth.sign_up(data)


@router.post("/login", response_model=AuthSessionRead)
async def login(data: LoginRequest):
    return await supabase_auth.sign_in_with_password(data)


@router.get("/oauth/{provider}")
async def oauth(provider: str, redirect_to: str = Query(...)):
    return RedirectResponse(supabase_auth.oauth_authorize_url(provider, redirect_to))


@router.get("/me", response_model=ProfileRead)
async def read_me(
    current_user: CurrentUser = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    return await service.get_profile(current_user.id)


@router.patch("/me", response_model=ProfileRead)
async def update_me(
    data: ProfileUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    return await service.update_profile(current_user.id, data)
