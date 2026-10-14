import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...core.config import get_settings
from ...core.db import get_db
from ..problem_details import AppError
from ...core.limiter import limiter
from ...core.security import (
    create_access_token,
    generate_reset_token,
    hash_password,
    hash_reset_token,
    verify_password,
)
from ...models import PasswordResetToken, User
from ...schemas.auth import (
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    Token,
    UserCreate,
    UserOut,
)

logger = logging.getLogger("fastappi_notification")

router = APIRouter(prefix="/auth", tags=["auth"])

# Hash "señuelo" con la forma de uno real. Cuando el email no existe, igual
# corremos una verificación contra este valor para que el tiempo de respuesta
# no delate si el email está registrado (mitiga enumeración por timing).
_DUMMY_HASH = hash_password("dummy-password-for-constant-time-check")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # La unicidad la garantiza la constraint de la base, no un chequeo
        # previo: así dos registros concurrentes no pueden colarse ambos.
        db.rollback()
        raise AppError(status.HTTP_409_CONFLICT, "Email already registered", "conflict")
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
@limiter.limit(get_settings().login_rate_limit)
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)) -> Token:
    user = db.scalar(select(User).where(User.email == payload.email))

    # Verificamos siempre (aun sin usuario) para no filtrar por timing y para
    # devolver un único error genérico: el login no revela qué emails existen.
    hashed = user.hashed_password if user else _DUMMY_HASH
    valid = verify_password(payload.password, hashed)

    if not user or not valid:
        raise AppError(status.HTTP_401_UNAUTHORIZED, "Invalid credentials", "unauthorized")

    return Token(access_token=create_access_token(str(user.id)))


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)) -> dict:
    """Siempre responde igual, exista o no el email (criterios 5 y 8).

    Si el usuario existe, generamos un token y (en un sistema real) lo
    mandaríamos por email. Acá el envío es simulado: lo dejamos en el log.
    """
    settings = get_settings()
    user = db.scalar(select(User).where(User.email == payload.email))
    if user:
        raw, token_hash = generate_reset_token()
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.now(timezone.utc)
                + timedelta(minutes=settings.reset_token_expire_minutes),
            )
        )
        db.commit()
        logger.info("Password reset token for user %s: %s", user.id, raw)

    return {"message": "If the email exists, a reset link was sent"}


@router.post("/password-reset/confirm", status_code=status.HTTP_200_OK)
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)) -> dict:
    token_hash = hash_reset_token(payload.token)
    now = datetime.now(timezone.utc)

    reset = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used.is_(False),
            PasswordResetToken.expires_at > now,
        )
    )
    if reset is None:
        raise AppError(status.HTTP_400_BAD_REQUEST, "Invalid or expired token", "invalid_token")

    user = db.get(User, reset.user_id)
    user.hashed_password = hash_password(payload.new_password)
    reset.used = True
    db.commit()

    return {"message": "Password updated"}
