from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

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
from app.services.breached_passwords import is_password_breached

from app.services.password_policy import (
    PasswordProblem,
    check_password,
    normalize_password,
)

from app.services.username_policy import (
    UsernameProblem,
    check_username,
    normalize_username,
)

class EmailAlreadyRegisteredError(Exception):
    pass

class WeakPasswordError(Exception):
    """Raised when a new password fails the policy. Carries every problem
    found, as codes the route/frontend can turn into messages."""

    def __init__(self, problems: list[PasswordProblem]):
        self.problems = problems
        super().__init__(", ".join(p.value for p in problems))

class InvalidUsernameError(Exception):
    """Username fails the format rules; carries every problem as codes."""

    def __init__(self, problems: list[UsernameProblem]):
        self.problems = problems
        super().__init__(", ".join(p.value for p in problems))


class UsernameTakenError(Exception):
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

def _violated_constraint(exc: IntegrityError) -> str | None:
    """Name of the unique/check constraint that failed, if the driver exposes it.

    With asyncpg the name lives on exc.orig.__cause__ (verified against the
    real database); exc.orig itself has no constraint_name.
    """
    cause = getattr(exc.orig, "__cause__", None)
    return getattr(cause, "constraint_name", None)

def validate_username(raw_username: str) -> str:
    """Normalize, then run the format rules.

    Returns the NORMALIZED username; callers must store the returned value,
    never the raw input. Raises InvalidUsernameError carrying every problem
    found. Pure (no DB): uniqueness is the caller's job.
    """
    username = normalize_username(raw_username)
    problems = check_username(
        username,
        min_length=settings.username_min_length,
        max_length=settings.username_max_length,
    )
    if problems:
        raise InvalidUsernameError(problems)
    return username

async def validate_new_password(raw_password: str, *, email: str) -> str:
    """Normalize, then run the policy and the breach check.

    Returns the NORMALIZED password. Callers must hash the returned value,
    never the raw input, or login (which normalizes) would not match.
    Raises WeakPasswordError carrying every problem found.
    """
    password = normalize_password(raw_password)
    problems = check_password(
        password,
        email=email,
        min_length=settings.password_min_length,
        max_bytes=settings.password_max_bytes,
    )
    if problems:
        raise WeakPasswordError(problems)
    if settings.hibp_enabled and await is_password_breached(
        password, timeout_s=settings.hibp_timeout_s
    ):
        raise WeakPasswordError([PasswordProblem.BREACHED])
    return password


async def register_user(db: AsyncSession, user_in: UserCreate) -> User:
    # 1. Cheap local checks first: no network, no DB, no bcrypt.
    username = validate_username(user_in.username)
    # 2. Password policy + breach lookup, shared with reset/change-password.
    #    Returns the NORMALIZED password; that is what we must hash below.
    password = await validate_new_password(user_in.password, email=user_in.email)

    # 3. Friendly pre-checks (the fast path).
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none() is not None:
        raise EmailAlreadyRegisteredError(f"Email {user_in.email} is already registered")

    result = await db.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none() is not None:
        raise UsernameTakenError(f"Username {username} is already taken")

    new_user = User(
        email=user_in.email,
        username=username,
        name=user_in.name,
        hashed_password=hash_password(password),
    )
    db.add(new_user)

    # 4. Backstop for the race: two requests can both pass the pre-checks and
    #    then collide on the unique constraint. Translate by constraint name,
    #    and never log or return str(exc): it contains the failing row.
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        constraint = _violated_constraint(exc)
        if constraint == "users_email_key":
            raise EmailAlreadyRegisteredError("Email is already registered") from None
        if constraint == "users_username_key":
            raise UsernameTakenError("Username is already taken") from None
        raise  # unknown constraint = a bug; stay loud

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

    if user is None or not verify_password(
        normalize_password(credentials.password), user.hashed_password
    ):
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

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise InvalidRefreshTokenError("Refresh token has already been used")

    return new_access_token, new_refresh_token

async def update_profile(
    db: AsyncSession,
    user: User,
    *,
    name: str | None = None,
    username: str | None = None,
) -> User:
    """Apply a partial profile update to `user` and return it.

    None means "not sent, leave alone" (the route passes only fields the
    client actually sent). The name arrives already trimmed and length-checked
    by the schema. A username is validated ONLY when sent, so accounts with a
    legacy backfilled username can still change their name.

    Raises InvalidUsernameError or UsernameTakenError.
    """
    if username is not None:
        new_username = validate_username(username)
        # Saving your own unchanged username is a no-op, never "taken".
        if new_username != user.username:
            result = await db.execute(
                select(User).where(
                    User.username == new_username, User.id != user.id
                )
            )
            if result.scalar_one_or_none() is not None:
                raise UsernameTakenError("Username is already taken")
            user.username = new_username

    if name is not None:
        user.name = name

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        if _violated_constraint(exc) == "users_username_key":
            raise UsernameTakenError("Username is already taken") from None
        raise  # unknown constraint = a bug; stay loud

    await db.refresh(user)
    return user