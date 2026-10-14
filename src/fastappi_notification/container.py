"""Raíz de composición: único lugar que conoce los canales concretos (ADR-004, ADR-005).

Agregar un canal = su política + su gateway registrados aquí; nada más cambia.
`api/deps.py` solo expone estas fábricas como `Depends()`.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from .application.channel_gateway_registry import ChannelGatewayRegistry
from .application.deliver_notification import DeliverNotification
from .application.use_cases.create_notification import CreateNotification
from .application.use_cases.delete_notification import DeleteNotification
from .application.use_cases.get_my_notification import GetMyNotification
from .application.use_cases.list_my_notifications import ListMyNotifications
from .application.use_cases.revise_notification import ReviseNotification
from .domain.channels import ChannelPolicyRegistry, EmailPolicy, PushPolicy, SmsPolicy
from .infrastructure.channels import (
    SimulatedEmailGateway,
    SimulatedPushGateway,
    SimulatedSmsGateway,
)
from .infrastructure.clock import SystemClock, UuidIdGenerator
from .infrastructure.persistence import SqlAlchemyNotificationRepository

# Piezas sin estado: se crean una vez.
clock = SystemClock()
ids = UuidIdGenerator()
policies = ChannelPolicyRegistry([EmailPolicy(), SmsPolicy(), PushPolicy()])
gateways = ChannelGatewayRegistry(
    [SimulatedEmailGateway(clock), SimulatedSmsGateway(clock), SimulatedPushGateway(clock)]
)


def notification_repository(session: Session) -> SqlAlchemyNotificationRepository:
    return SqlAlchemyNotificationRepository(session)


def _deliver(session: Session) -> DeliverNotification:
    return DeliverNotification(notification_repository(session), gateways)


def create_notification(session: Session) -> CreateNotification:
    return CreateNotification(policies, gateways, ids, clock, _deliver(session))


def revise_notification(session: Session) -> ReviseNotification:
    return ReviseNotification(notification_repository(session), policies, clock, _deliver(session))


def list_my_notifications(session: Session) -> ListMyNotifications:
    return ListMyNotifications(notification_repository(session))


def get_my_notification(session: Session) -> GetMyNotification:
    return GetMyNotification(notification_repository(session))


def delete_notification(session: Session) -> DeleteNotification:
    return DeleteNotification(notification_repository(session))
