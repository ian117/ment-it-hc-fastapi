"""Errores de dominio. Sin dependencias externas; la capa `api/` los traduce a HTTP."""

from __future__ import annotations

from typing import Optional
from uuid import UUID


class NotificationNotFound(Exception):
    """La notificación no existe o no es del usuario (HTTP 404; ambos casos son indistinguibles)."""

    def __init__(self, id: Optional[UUID] = None) -> None:
        self.id = id
        super().__init__("Notification not found" if id is None else f"Notification not found: {id}")


class NotificationNotEditable(Exception):
    """`revise` solo es válido desde `failed` (HTTP 409)."""

    def __init__(self, message: str = "Only failed notifications can be edited") -> None:
        super().__init__(message)


class InvalidNotificationTransition(Exception):
    """`mark_sent` / `mark_failed` fuera de `pending` (bug interno, no un 409 de cliente)."""

    def __init__(
        self, message: str = "Invalid notification state transition"
    ) -> None:
        super().__init__(message)


class ChannelRuleViolation(Exception):
    """El borrador incumple las reglas del canal (HTTP 400 con `errors` por campo).

    `violations` es una lista no vacía de `{"field": ..., "message": ...}`; las claves
    coinciden con el Problem Details para que el mapeo sea directo (ADR-010).
    """

    def __init__(self, violations: list[dict[str, str]]) -> None:
        if not violations:
            raise ValueError("ChannelRuleViolation requires at least one violation")
        self.violations = violations
        super().__init__("; ".join(f"{v['field']}: {v['message']}" for v in violations))


class UnknownChannel(Exception):
    """El canal no está en el registro (HTTP 400, ADR-004)."""

    def __init__(self, channel: str) -> None:
        self.channel = channel
        super().__init__(f"Unknown channel: {channel}")


class InvalidEmail(Exception):
    """El email no tiene formato válido (HTTP 400 `validation-error`, campo `email`)."""

    def __init__(self, message: str = "Invalid email address") -> None:
        super().__init__(message)


class EmailAlreadyRegistered(Exception):
    """Ya existe un usuario con ese email (HTTP 409)."""

    def __init__(self, message: str = "Email already registered") -> None:
        super().__init__(message)


class InvalidCredentials(Exception):
    """Email o contraseña incorrectos; no distingue cuál (HTTP 401)."""

    def __init__(self, message: str = "Invalid credentials") -> None:
        super().__init__(message)


class InvalidResetToken(Exception):
    """Token de reseteo inexistente, vencido o ya usado (HTTP 400)."""

    def __init__(self, message: str = "Invalid or expired reset token") -> None:
        super().__init__(message)


class UserNotFound(Exception):
    """El usuario no existe (p. ej. JWT válido de un usuario ya borrado; HTTP 401)."""

    def __init__(self, id: Optional[UUID] = None) -> None:
        self.id = id
        super().__init__("User not found" if id is None else f"User not found: {id}")
