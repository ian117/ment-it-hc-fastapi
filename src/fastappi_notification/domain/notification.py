"""Entidad `Notification` y su máquina de estados (diseño 2.1-2.2, ADR-009).

Dominio puro: solo stdlib. La hora siempre llega como parámetro; nunca se lee un reloj.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from fastappi_notification.domain.errors import (
    InvalidNotificationTransition,
    NotificationNotEditable,
)

# El registro de canales vive en la raíz de composición; el dominio solo los nombra.
ChannelName = str


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class Notification:
    """Los atributos son de solo lectura desde fuera: el estado cambia únicamente
    mediante `mark_sent`, `mark_failed` y `revise`, que validan antes de mutar."""

    __slots__ = (
        "_id",
        "_owner_id",
        "_title",
        "_content",
        "_channel",
        "_recipient",
        "_status",
        "_attempts",
        "_error_message",
        "_sent_at",
        "_created_at",
        "_updated_at",
    )

    def __init__(
        self,
        *,
        id: UUID,
        owner_id: UUID,
        title: str,
        content: str,
        channel: ChannelName,
        recipient: str,
        status: NotificationStatus,
        attempts: int,
        error_message: Optional[str],
        sent_at: Optional[datetime],
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self._id = id
        self._owner_id = owner_id
        self._title = title
        self._content = content
        self._channel = channel
        self._recipient = recipient
        self._status = status
        self._attempts = attempts
        self._error_message = error_message
        self._sent_at = sent_at
        self._created_at = created_at
        self._updated_at = updated_at

    # -- Constructores ------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        id: UUID,
        owner_id: UUID,
        title: str,
        content: str,
        channel: ChannelName,
        recipient: str,
        now: datetime,
    ) -> Notification:
        return cls(
            id=id,
            owner_id=owner_id,
            title=title,
            content=content,
            channel=channel,
            recipient=recipient,
            status=NotificationStatus.PENDING,
            attempts=0,
            error_message=None,
            sent_at=None,
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: UUID,
        owner_id: UUID,
        title: str,
        content: str,
        channel: ChannelName,
        recipient: str,
        status: NotificationStatus | str,
        attempts: int,
        error_message: Optional[str],
        sent_at: Optional[datetime],
        created_at: datetime,
        updated_at: datetime,
    ) -> Notification:
        """Reconstruye desde estado persistido, sin validar transiciones."""
        return cls(
            id=id,
            owner_id=owner_id,
            title=title,
            content=content,
            channel=channel,
            recipient=recipient,
            status=NotificationStatus(status),
            attempts=attempts,
            error_message=error_message,
            sent_at=sent_at,
            created_at=created_at,
            updated_at=updated_at,
        )

    # -- Lectura ------------------------------------------------------------

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def owner_id(self) -> UUID:
        return self._owner_id

    @property
    def title(self) -> str:
        return self._title

    @property
    def content(self) -> str:
        return self._content

    @property
    def channel(self) -> ChannelName:
        return self._channel

    @property
    def recipient(self) -> str:
        return self._recipient

    @property
    def status(self) -> NotificationStatus:
        return self._status

    @property
    def attempts(self) -> int:
        return self._attempts

    @property
    def error_message(self) -> Optional[str]:
        return self._error_message

    @property
    def sent_at(self) -> Optional[datetime]:
        return self._sent_at

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    # -- Transiciones -------------------------------------------------------

    def mark_sent(self, at: datetime) -> None:
        self._require_pending("mark a notification as sent")
        self._status = NotificationStatus.SENT
        self._sent_at = at
        self._error_message = None
        self._attempts += 1
        self._updated_at = at

    def mark_failed(self, reason: str, at: datetime) -> None:
        self._require_pending("mark a notification as failed")
        self._status = NotificationStatus.FAILED
        self._error_message = reason
        self._attempts += 1
        self._updated_at = at

    def ensure_editable(self) -> None:
        """Única regla de editabilidad: solo `failed` (409). La reutiliza `revise`."""
        if self._status is not NotificationStatus.FAILED:
            raise NotificationNotEditable()

    def revise(
        self,
        at: datetime,
        *,
        title: Optional[str] = None,
        content: Optional[str] = None,
        recipient: Optional[str] = None,
    ) -> None:
        self.ensure_editable()
        if title is not None:
            self._title = title
        if content is not None:
            self._content = content
        if recipient is not None:
            self._recipient = recipient
        self._status = NotificationStatus.PENDING
        self._error_message = None
        self._updated_at = at

    def _require_pending(self, action: str) -> None:
        if self._status is not NotificationStatus.PENDING:
            raise InvalidNotificationTransition(
                f"Cannot {action} from status '{self._status.value}'; expected 'pending'"
            )
