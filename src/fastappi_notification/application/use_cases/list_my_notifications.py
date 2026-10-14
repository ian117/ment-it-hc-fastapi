from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastappi_notification.application.ports import NotificationRepository
from fastappi_notification.domain.notification import Notification


@dataclass(frozen=True)
class ListResult:
    data: list[Notification]
    total: int
    page: int
    limit: int


class ListMyNotifications:
    """No valida paginación: eso es de `api/` (ADR-011)."""

    def __init__(self, repo: NotificationRepository) -> None:
        self._repo = repo

    def execute(self, owner_id: UUID, page: int, limit: int) -> ListResult:
        items, total = self._repo.list_by_owner(owner_id, page, limit)
        return ListResult(data=items, total=total, page=page, limit=limit)
