from __future__ import annotations

from uuid import UUID

from fastappi_notification.application.ports import NotificationRepository
from fastappi_notification.domain.errors import NotificationNotFound


class DeleteNotification:
    def __init__(self, repo: NotificationRepository) -> None:
        self._repo = repo

    def execute(self, owner_id: UUID, id: UUID) -> None:
        if not self._repo.delete(id, owner_id):
            raise NotificationNotFound(id)
