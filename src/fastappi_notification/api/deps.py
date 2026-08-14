import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..core.errors import AppError
from ..core.security import decode_access_token
from ..models import User

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Resuelve el usuario autenticado a partir del Bearer token.

    Cualquier fallo (sin token, token inválido/expirado, usuario inexistente)
    devuelve el mismo 401 genérico: no distinguimos casos hacia afuera.
    """
    if credentials is None:
        raise AppError(401, "Not authenticated", "unauthorized")

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise AppError(401, "Invalid or expired token", "unauthorized")

    if payload.get("type") != "access":
        raise AppError(401, "Invalid token", "unauthorized")

    user_id = payload.get("sub")
    user = db.scalar(select(User).where(User.id == int(user_id))) if user_id else None
    if user is None:
        raise AppError(401, "Invalid token", "unauthorized")

    return user
