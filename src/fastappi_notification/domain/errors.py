from __future__ import annotations

"""Errores de dominio. Sin dependencias externas; la capa `api/` los traduce a HTTP."""


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
