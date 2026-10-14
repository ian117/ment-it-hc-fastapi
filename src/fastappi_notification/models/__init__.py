"""Modelos ORM del auth heredado. Los de notificaciones viven en
`infrastructure/persistence`. Se importan todos acá para que `Base.metadata`
los conozca al generar migraciones o crear tablas."""

from ..infrastructure.persistence.notification_model import NotificationModel
from .password_reset import PasswordResetToken
from .user import User

__all__ = ["User", "NotificationModel", "PasswordResetToken"]
