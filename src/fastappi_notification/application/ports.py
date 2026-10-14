"""Puertos de la capa de aplicación (ADR-011). Solo stdlib + dominio.

Las implementaciones (SQLAlchemy, gateways simulados, reloj del sistema) viven en
`infrastructure/` y se conectan en la raíz de composición.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol
from uuid import UUID

from fastappi_notification.domain.channels import OutboundMessage
from fastappi_notification.domain.notification import Notification


@dataclass(frozen=True)
class DeliveryResult:
    ok: bool
    at: datetime
    detail: Optional[str] = None


class NotificationRepository(Protocol):
    def save(self, notification: Notification) -> None:
        """Inserta o actualiza (upsert por `id`)."""
        ...

    def find_by_id(self, id: UUID, owner_id: UUID) -> Optional[Notification]:
        """`None` si no existe **o** no pertenece a `owner_id`."""
        ...

    def list_by_owner(
        self, owner_id: UUID, page: int, limit: int
    ) -> tuple[list[Notification], int]:
        """Página (1-based) de las notificaciones del dueño, `created_at desc, id desc`,
        y el total sin paginar."""
        ...

    def delete(self, id: UUID, owner_id: UUID) -> bool:
        """`False` si no existe o no pertenece a `owner_id`."""
        ...


class ChannelGateway(Protocol):
    channel: str

    def deliver(self, message: OutboundMessage) -> DeliveryResult: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new_id(self) -> UUID: ...
