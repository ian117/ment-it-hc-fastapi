"""Solo expone `Depends()`: el cableado real vive en `container.py`."""

from uuid import UUID

from fastapi import Depends, HTTPException, Path
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .. import container
from ..application.use_cases.confirm_password_reset import ConfirmPasswordReset
from ..application.use_cases.create_notification import CreateNotification
from ..application.use_cases.delete_notification import DeleteNotification
from ..application.use_cases.get_current_user import GetCurrentUser
from ..application.use_cases.get_my_notification import GetMyNotification
from ..application.use_cases.list_my_notifications import ListMyNotifications
from ..application.use_cases.login import Login
from ..application.use_cases.register_user import RegisterUser
from ..application.use_cases.request_password_reset import RequestPasswordReset
from ..application.use_cases.revise_notification import ReviseNotification
from ..core.config import get_settings
from ..core.db import get_db
from ..domain.errors import NotificationNotFound

_bearer = HTTPBearer(auto_error=False)
_UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}


def current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UUID:
    """UUID del usuario autenticado, sin consultar la base (ADR-014).

    Valida firma, expiración, `type` y que `sub` sea UUID. Cualquier fallo es el
    mismo 401: no distinguimos casos hacia afuera.
    """
    if credentials is None:
        raise HTTPException(401, "Not authenticated", headers=_UNAUTHORIZED_HEADERS)
    user_id = container.token_verifier.verify(credentials.credentials)
    if user_id is None:
        raise HTTPException(401, "Invalid or expired token", headers=_UNAUTHORIZED_HEADERS)
    return user_id


def expose_reset_token() -> bool:
    """`resetToken` solo se devuelve fuera de producción (ADR-014)."""
    return get_settings().environment != "production"


def notification_id(id: str = Path(..., json_schema_extra={"format": "uuid"})) -> UUID:
    """Un id con formato inválido equivale a uno inexistente: 404 (ADR-012)."""
    try:
        return UUID(id)
    except ValueError:
        raise NotificationNotFound() from None


def register_user_use_case(db: Session = Depends(get_db)) -> RegisterUser:
    return container.register_user(db)


def login_use_case(db: Session = Depends(get_db)) -> Login:
    return container.login(db)


def get_current_user_use_case(db: Session = Depends(get_db)) -> GetCurrentUser:
    return container.get_current_user(db)


def request_password_reset_use_case(db: Session = Depends(get_db)) -> RequestPasswordReset:
    return container.request_password_reset(db)


def confirm_password_reset_use_case(db: Session = Depends(get_db)) -> ConfirmPasswordReset:
    return container.confirm_password_reset(db)


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
