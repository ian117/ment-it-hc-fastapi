"""Fakes en memoria de los puertos de `application/` (sin framework ni base de datos)."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastappi_notification.application.channel_gateway_registry import ChannelGatewayRegistry
from fastappi_notification.application.deliver_notification import DeliverNotification
from fastappi_notification.application.ports import DeliveryResult
from fastappi_notification.application.use_cases.create_notification import CreateNotification
from fastappi_notification.application.use_cases.delete_notification import DeleteNotification
from fastappi_notification.application.use_cases.get_my_notification import GetMyNotification
from fastappi_notification.application.use_cases.list_my_notifications import ListMyNotifications
from fastappi_notification.application.use_cases.revise_notification import ReviseNotification
from fastappi_notification.domain.channels import (
    ChannelPolicyRegistry,
    EmailPolicy,
    OutboundMessage,
    PushPolicy,
    SmsPolicy,
)
from fastappi_notification.domain.notification import Notification, NotificationStatus

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
OWNER = UUID("aaaaaaaa-0000-0000-0000-000000000001")
OTHER = UUID("bbbbbbbb-0000-0000-0000-000000000002")
SMS_OK = "+5219611234567"
SMS_OTHER = "+5215512345678"


class InMemoryNotificationRepository:
    """Guarda copias (como haría una base de datos) y un historial de `save`.

    `saved_statuses` guarda el status de cada `save`, en orden. `events` (log compartido
    opcional) recibe `("save", status)` para verificar el orden respecto a `deliver`.
    """

    def __init__(self, events: Optional[list[tuple[str, str]]] = None) -> None:
        self._items: dict[UUID, Notification] = {}
        self.saved_statuses: list[NotificationStatus] = []
        self.events = events if events is not None else []

    def save(self, notification: Notification) -> None:
        self._items[notification.id] = copy.deepcopy(notification)
        self.saved_statuses.append(notification.status)
        self.events.append(("save", notification.status.value))

    def find_by_id(self, id: UUID, owner_id: UUID) -> Optional[Notification]:
        stored = self._items.get(id)
        if stored is None or stored.owner_id != owner_id:
            return None
        return copy.deepcopy(stored)

    def list_by_owner(
        self, owner_id: UUID, page: int, limit: int
    ) -> tuple[list[Notification], int]:
        own = [n for n in self._items.values() if n.owner_id == owner_id]
        own.sort(key=lambda n: (n.created_at, n.id), reverse=True)
        start = (page - 1) * limit
        return [copy.deepcopy(n) for n in own[start : start + limit]], len(own)

    def delete(self, id: UUID, owner_id: UUID) -> bool:
        stored = self._items.get(id)
        if stored is None or stored.owner_id != owner_id:
            return False
        del self._items[id]
        return True

    # -- ayudas de test --
    def is_empty(self) -> bool:
        return not self._items

    def stored(self, id: UUID) -> Notification:
        return self._items[id]


class FakeClock:
    def __init__(self, start: datetime = T0) -> None:
        self._now = start

    def now(self) -> datetime:
        return self._now

    def set(self, value: datetime) -> None:
        self._now = value

    def advance(self, **kwargs: float) -> datetime:
        self._now += timedelta(**kwargs)
        return self._now


class SequentialIdGenerator:
    """UUIDs deterministas: 00000000-...-000000000001, ...0002, etc."""

    def __init__(self, start: int = 1) -> None:
        self._next = start

    def new_id(self) -> UUID:
        value = UUID(int=self._next)
        self._next += 1
        return value


class FakeChannelGateway:
    """Configurable: entrega ok (por defecto), falla con `detail` o lanza una excepción.

    Al entregar registra `("deliver", <status ya persistido>)` en el log compartido.
    """

    def __init__(
        self,
        channel: str,
        repo: InMemoryNotificationRepository,
        *,
        ok: bool = True,
        detail: Optional[str] = None,
        raises: Optional[Exception] = None,
        clock: Optional[FakeClock] = None,
    ) -> None:
        self.channel = channel
        self.ok = ok
        self.detail = detail
        self.raises = raises
        self.messages: list[OutboundMessage] = []
        self._repo = repo
        self._clock = clock or FakeClock()

    def deliver(self, message: OutboundMessage) -> DeliveryResult:
        persisted = self._repo.saved_statuses[-1].value if self._repo.saved_statuses else "none"
        self._repo.events.append(("deliver", persisted))
        self.messages.append(message)
        if self.raises is not None:
            raise self.raises
        return DeliveryResult(ok=self.ok, at=self._clock.now(), detail=self.detail)

    @property
    def calls(self) -> int:
        return len(self.messages)


@dataclass
class World:
    """Cableado completo de los casos de uso con fakes."""

    events: list[tuple[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.repo = InMemoryNotificationRepository(self.events)
        self.clock = FakeClock()
        self.ids = SequentialIdGenerator()
        self.sms = FakeChannelGateway("sms", self.repo, clock=self.clock)
        self.email = FakeChannelGateway("email", self.repo, clock=self.clock)
        self.push = FakeChannelGateway("push", self.repo, clock=self.clock)
        self.gateways = ChannelGatewayRegistry([self.sms, self.email, self.push])
        self.policies = ChannelPolicyRegistry([SmsPolicy(), EmailPolicy(), PushPolicy()])
        self.deliver = DeliverNotification(self.repo, self.gateways)
        self.create = CreateNotification(
            self.policies, self.gateways, self.ids, self.clock, self.deliver
        )
        self.revise = ReviseNotification(self.repo, self.policies, self.clock, self.deliver)
        self.list = ListMyNotifications(self.repo)
        self.get = GetMyNotification(self.repo)
        self.delete = DeleteNotification(self.repo)
