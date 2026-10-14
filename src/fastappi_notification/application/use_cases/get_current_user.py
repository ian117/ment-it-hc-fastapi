from __future__ import annotations

from uuid import UUID

from fastappi_notification.application.ports import UserRepository
from fastappi_notification.domain.errors import UserNotFound
from fastappi_notification.domain.user import User


class GetCurrentUser:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def execute(self, *, user_id: UUID) -> User:
        user = self._users.find_by_id(user_id)
        if user is None:
            raise UserNotFound(user_id)
        return user
