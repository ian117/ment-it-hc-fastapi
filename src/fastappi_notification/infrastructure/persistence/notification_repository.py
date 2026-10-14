"""Adaptador SQLAlchemy del puerto `NotificationRepository`.

Cada `save` y `delete` es una transacción corta (ADR-008, ADR-012).
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ...domain.notification import Notification
from .notification_mapper import NotificationMapper
from .notification_model import NotificationModel


class SqlAlchemyNotificationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, notification: Notification) -> None:
        try:
            self._session.merge(NotificationMapper.to_model(notification))
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

    def find_by_id(self, id: UUID, owner_id: UUID) -> Optional[Notification]:
        model = self._session.scalar(
            select(NotificationModel).where(
                NotificationModel.id == id, NotificationModel.user_id == owner_id
            )
        )
        return None if model is None else NotificationMapper.to_domain(model)

    def list_by_owner(
        self, owner_id: UUID, page: int, limit: int
    ) -> tuple[list[Notification], int]:
        total = self._session.scalar(
            select(func.count()).select_from(NotificationModel).where(NotificationModel.user_id == owner_id)
        )
        rows = self._session.scalars(
            select(NotificationModel)
            .where(NotificationModel.user_id == owner_id)
            .order_by(NotificationModel.created_at.desc(), NotificationModel.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
        return [NotificationMapper.to_domain(m) for m in rows], total or 0

    def delete(self, id: UUID, owner_id: UUID) -> bool:
        try:
            result = self._session.execute(
                delete(NotificationModel).where(
                    NotificationModel.id == id, NotificationModel.user_id == owner_id
                )
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        return result.rowcount > 0
