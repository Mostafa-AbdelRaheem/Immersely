import logging
from datetime import datetime, timedelta, timezone

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Cookie,
    Depends,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.db import get_db
from app.core.limiter import limiter
from app.core.security import generate_csrf_token, hash_token
from app.models.user import User

from app.schemas.user import (
    ChangePasswordIn,
    ForgotPasswordIn,
    ProfileUpdateIn,
    ResetPasswordIn,
    UserCreate,
    UserLogin,
    UserOut,
    VerifyEmailIn,
)
from app.services.auth import (
    AccountLockedError,
    CurrentPasswordIncorrectError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    InvalidUsernameError,
    SamePasswordError,
    UsernameTakenError,
    WeakPasswordError,
    change_password,
    login_user,
    refresh_tokens,
    register_user,
    update_profile,
)

from app.services.email_sender import (
    EmailMessage,
    EmailSender,
    EmailSendError,
    get_email_sender,
)

from app.services.email_tokens import InvalidTokenError
from app.services.email_verification import (
    EmailAlreadyVerifiedError,
    send_verification_email,
    verify_email,
)

from app.services.password_reset import request_password_reset, reset_password
from app.services.sessions import revoke_user_refresh_tokens



router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger(__name__)

REFRESH_COOKIE_NAME = "refresh_token"
CSRF_COOKIE_NAME = "csrf_token"


def _set_auth_cookies(response: Response, refresh_token: str) -> None:
    csrf_token = generate_csrf_token()

    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=False,  # True once served over HTTPS
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/auth",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        samesite="lax",
        secure=False,  # True once served over HTTPS
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/",
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request,
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
    sender: EmailSender = Depends(get_email_sender),
):
    try:
        user = await register_user(db, user_in)
    except InvalidUsernameError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_username",
                "problems": [p.value for p in exc.problems],
            },
        )

    except WeakPasswordError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "weak_password",
                "problems": [p.value for p in exc.problems],
            },
        )

    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "email_taken"},
        )
    except UsernameTakenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "username_taken"},
        )

    # Best-effort: the account exists either way. A failed send is tolerated
    # (the user can request a resend); anything else is a bug and stays loud.
    try:
        await send_verification_email(db, sender, user)
    except EmailSendError as exc:
        # Class name only: provider messages can echo the address back.
        logger.warning(
            "Verification email failed after registration: %s", type(exc).__name__
        )
    return user


@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    try:
        access_token, refresh_token = await login_user(db, credentials)
    except AccountLockedError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    _set_auth_cookies(response, refresh_token)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/refresh")
@limiter.limit("10/minute")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE_NAME),
    x_csrf_token: str | None = Header(default=None),
):
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided",
        )

    if not csrf_cookie or not x_csrf_token or csrf_cookie != x_csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing or invalid",
        )

    try:
        new_access_token, new_refresh_token = await refresh_tokens(db, refresh_token)
    except InvalidRefreshTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    _set_auth_cookies(response, new_refresh_token)
    return {"access_token": new_access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/auth")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")
    return {"detail": "Logged out"}

@router.post("/logout-all")
@limiter.limit("5/minute")
async def logout_all(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Revoke EVERY session, this device included (no except_token_hash).
    # Bearer token is the authority, so no CSRF check, as in change-password.
    await revoke_user_refresh_tokens(db, current_user.id)
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/auth")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")
    return {"detail": "Logged out everywhere"}


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
@limiter.limit("10/minute")
async def update_me(
    request: Request,
    body: ProfileUpdateIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await update_profile(
            db, current_user, **body.model_dump(exclude_unset=True)
        )
    except InvalidUsernameError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_username",
                "problems": [p.value for p in exc.problems],
            },
        )
    except UsernameTakenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "username_taken"},
        )


@router.post("/change-password")
@limiter.limit("5/minute")
async def change_password_endpoint(
    request: Request,
    body: ChangePasswordIn,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    sender: EmailSender = Depends(get_email_sender),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
):
    # The cookie only identifies which session to spare; the bearer token is
    # the authority, so no CSRF check is needed here. No cookie = revoke all.
    keep_hash = hash_token(refresh_token) if refresh_token else None
    try:
        notice = await change_password(
            db,
            current_user,
            body.current_password,
            body.new_password,
            keep_token_hash=keep_hash,
        )
    except CurrentPasswordIncorrectError:
        # 400, never 401: a 401 makes the client try a refresh and possibly log out.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "current_password_incorrect"},
        )
    except SamePasswordError:
        raise HTTPException(
            status_code=422,
            detail={"code": "same_as_current"},
        )
    except WeakPasswordError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "weak_password",
                "problems": [p.value for p in exc.problems],
            },
        )
    background_tasks.add_task(_send_in_background, sender, notice)
    return {"detail": "Password updated"}


@router.post("/verify-email")
@limiter.limit("10/minute")
async def verify_email_endpoint(
    request: Request,
    body: VerifyEmailIn,
    db: AsyncSession = Depends(get_db),
):
    try:
        await verify_email(db, body.token)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_token"},
        )
    return {"detail": "Email verified"}


@router.post("/resend-verification")
@limiter.limit("3/minute")
async def resend_verification(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    sender: EmailSender = Depends(get_email_sender),
):
    try:
        await send_verification_email(db, sender, current_user)
    except EmailAlreadyVerifiedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "already_verified"},
        )
    except EmailSendError as exc:
        # Class name only: provider messages can echo the address back.
        logger.warning("Verification email failed to send: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "email_send_failed"},
        )
    return {"detail": "Verification email sent"}


# One constant for every forgot-password outcome (unknown email, cooldown, sent),
# so the response can never differ between them.
FORGOT_PASSWORD_RESPONSE = {
    "detail": "If an account exists for that email, we've sent a reset link."
}


async def _send_in_background(sender: EmailSender, message: EmailMessage) -> None:
    """Runs after the response. Holds no DB session, so neither mail latency nor
    a failure here can change what the client saw."""
    try:
        await sender.send(message)
    except EmailSendError as exc:
        # Class name only: provider messages can echo the address back.
        logger.warning("Background email failed to send: %s", type(exc).__name__)


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    body: ForgotPasswordIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    sender: EmailSender = Depends(get_email_sender),
):
    # None = unknown email OR cooldown active. Same response either way.
    message = await request_password_reset(db, body.email)
    if message is not None:
        background_tasks.add_task(_send_in_background, sender, message)
    return FORGOT_PASSWORD_RESPONSE


@router.post("/reset-password")
@limiter.limit("10/minute")
async def reset_password_endpoint(
    request: Request,
    body: ResetPasswordIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    sender: EmailSender = Depends(get_email_sender),
):
    try:
        notice = await reset_password(db, body.token, body.new_password)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_token"},
        )
    except WeakPasswordError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "weak_password",
                "problems": [p.value for p in exc.problems],
            },
        )
    background_tasks.add_task(_send_in_background, sender, notice)
    return {"detail": "Password updated"}