"""Traduce `NotificationModel` <-> `Notification` (dominio)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ...domain.notification import Notification
from .notification_model import NotificationModel


def _utc(value: Optional[datetime]) -> Optional[datetime]:
    return None if value is None else value.astimezone(timezone.utc)


class NotificationMapper:
    @staticmethod
    def to_domain(model: NotificationModel) -> Notification:
        return Notification.restore(
            id=model.id,
            owner_id=model.user_id,
            title=model.title,
            content=model.content,
            channel=model.channel,
            recipient=model.payload["recipient"],
            status=model.status,
            attempts=model.attempts,
            error_message=model.error_message,
            sent_at=_utc(model.sent_at),
            created_at=_utc(model.created_at),
            updated_at=_utc(model.updated_at),
        )

    @staticmethod
    def to_model(notification: Notification) -> NotificationModel:
        return NotificationModel(
            id=notification.id,
            user_id=notification.owner_id,
            title=notification.title,
            content=notification.content,
            channel=notification.channel,
            payload={"recipient": notification.recipient},
            status=notification.status.value,
            attempts=notification.attempts,
            error_message=notification.error_message,
            sent_at=notification.sent_at,
            created_at=notification.created_at,
            updated_at=notification.updated_at,
        )
