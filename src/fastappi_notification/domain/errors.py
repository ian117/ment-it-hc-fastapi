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
