"""Solo expone `Depends()`: el cableado real vive en `container.py`."""

from uuid import UUID

import jwt
from fastapi import Depends, Path
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import container
from ..application.use_cases.create_notification import CreateNotification
from ..application.use_cases.delete_notification import DeleteNotification
from ..application.use_cases.get_my_notification import GetMyNotification
from ..application.use_cases.list_my_notifications import ListMyNotifications
from ..application.use_cases.revise_notification import ReviseNotification
from ..core.db import get_db
from ..core.security import decode_access_token
from ..domain.errors import NotificationNotFound
from ..models import User
from .problem_details import AppError

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

    try:
        user_id = UUID(str(payload.get("sub")))
    except ValueError:
        raise AppError(401, "Invalid token", "unauthorized")

    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise AppError(401, "Invalid token", "unauthorized")

    return user


def notification_id(id: str = Path(..., json_schema_extra={"format": "uuid"})) -> UUID:
    """Un id con formato inválido equivale a uno inexistente: 404 (ADR-012)."""
    try:
        return UUID(id)
    except ValueError:
        raise NotificationNotFound() from None


def create_notification_use_case(db: Session = Depends(get_db)) -> CreateNotification:
    return container.create_notification(db)


def revise_notification_use_case(db: Session = Depends(get_db)) -> ReviseNotification:
    return container.revise_notification(db)


def list_my_notifications_use_case(db: Session = Depends(get_db)) -> ListMyNotifications:
    return container.list_my_notifications(db)


def get_my_notification_use_case(db: Session = Depends(get_db)) -> GetMyNotification:
    return container.get_my_notification(db)


def delete_notification_use_case(db: Session = Depends(get_db)) -> DeleteNotification:
    return container.delete_notification(db)
