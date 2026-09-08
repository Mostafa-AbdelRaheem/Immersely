from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.user import RefreshRequest, TokenPair, UserCreate, UserLogin, UserOut
from app.services.auth import (
    AccountLockedError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    login_user,
    refresh_tokens,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        user = await register_user(db, user_in)
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )
    return user


@router.post("/login", response_model=TokenPair)
@limiter.limit("5/minute")
async def login(request: Request, credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    try:
        access_token, refresh_token = await login_user(db, credentials)
    except AccountLockedError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPair)
@limiter.limit("10/minute")
async def refresh(request: Request, body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        access_token, refresh_token = await refresh_tokens(db, body.refresh_token)
    except InvalidRefreshTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user