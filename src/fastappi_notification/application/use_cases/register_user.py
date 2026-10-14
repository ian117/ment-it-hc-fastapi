from __future__ import annotations

from fastappi_notification.application.ports import (
    Clock,
    IdGenerator,
    PasswordHasher,
    UserRepository,
)
from fastappi_notification.domain.email import Email
from fastappi_notification.domain.errors import EmailAlreadyRegistered
from fastappi_notification.domain.user import User


class RegisterUser:
    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        ids: IdGenerator,
        clock: Clock,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._ids = ids
        self._clock = clock

    def execute(self, *, email: str, password: str) -> User:
        address = Email.create(email)  # InvalidEmail
        # Camino rápido: evita un hash inútil. La carrera real la resuelve `save`.
        if self._users.find_by_email(address) is not None:
            raise EmailAlreadyRegistered()
        user = User.create(
            id=self._ids.new_id(),
            email=address,
            password_hash=self._hasher.hash(password),
            now=self._clock.now(),
        )
        self._users.save(user)  # EmailAlreadyRegistered si otro ganó la carrera
        return user
