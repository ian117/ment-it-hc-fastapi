from __future__ import annotations

from uuid import UUID

from fastappi_notification.application.ports import NotificationRepository
from fastappi_notification.domain.errors import NotificationNotFound
from fastappi_notification.domain.notification import Notification


class GetMyNotification:
    def __init__(self, repo: NotificationRepository) -> None:
        self._repo = repo

    def execute(self, owner_id: UUID, id: UUID) -> Notification:
        notification = self._repo.find_by_id(id, owner_id)
        if notification is None:
            raise NotificationNotFound(id)
        return notification
