from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


_failed_login_attempts: dict[str, list[datetime]] = {}

LOCKOUT_THRESHOLD = 5
LOCKOUT_WINDOW = timedelta(seconds=60)


class AccountLockedError(Exception):
    pass

async def register_user(db: AsyncSession, user_in: UserCreate) -> User:
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalar_one_or_none()
    if existing_user is not None:
        raise EmailAlreadyRegisteredError(f"Email {user_in.email} is already registered")

    new_user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
    )
    db.add(new_user)
    await db.commit()

    return new_user


async def login_user(db: AsyncSession, credentials: UserLogin) -> tuple[str, str]:
    email = credentials.email
    now = datetime.now(timezone.utc)

    attempts = _failed_login_attempts.get(email, [])
    recent_attempts = [t for t in attempts if now - t < LOCKOUT_WINDOW]

    if len(recent_attempts) >= LOCKOUT_THRESHOLD:
        raise AccountLockedError(
            "Too many failed login attempts. Please try again in a minute."
        )

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(credentials.password, user.hashed_password):
        recent_attempts.append(now)
        _failed_login_attempts[email] = recent_attempts
        raise InvalidCredentialsError("Invalid email or password")

    _failed_login_attempts.pop(email, None)

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=expires_at,
        )
    )
    await db.commit()

    return access_token, refresh_token


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> tuple[str, str]:
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        raise InvalidRefreshTokenError("Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise InvalidRefreshTokenError("Token is not a refresh token")

    user_id = payload["sub"]
    token_hash = hash_token(refresh_token)

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored_token = result.scalar_one_or_none()

    if stored_token is None or stored_token.revoked_at is not None:
        raise InvalidRefreshTokenError("Refresh token has been revoked or reused")

    stored_token.revoked_at = datetime.now(timezone.utc)

    new_access_token = create_access_token(user_id)
    new_refresh_token = create_refresh_token(user_id)

    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    db.add(
        RefreshToken(
            user_id=stored_token.user_id,
            token_hash=hash_token(new_refresh_token),
            expires_at=expires_at,
        )
    )
    await db.commit()

    return new_access_token, new_refresh_token