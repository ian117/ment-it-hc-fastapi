"""Entidad `User` (diseño 2.1, ADR-013). Dominio puro: la hora llega por parámetro."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastappi_notification.domain.email import Email
from fastappi_notification.domain.password_hash import PasswordHash


class User:
    __slots__ = ("_id", "_email", "_password_hash", "_created_at", "_updated_at")

    def __init__(
        self,
        *,
        id: UUID,
        email: Email,
        password_hash: PasswordHash,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self._id = id
        self._email = email
        self._password_hash = password_hash
        self._created_at = created_at
        self._updated_at = updated_at

    @classmethod
    def create(
        cls, *, id: UUID, email: Email, password_hash: PasswordHash, now: datetime
    ) -> User:
        return cls(id=id, email=email, password_hash=password_hash, created_at=now, updated_at=now)

    @classmethod
    def restore(
        cls,
        *,
        id: UUID,
        email: Email,
        password_hash: PasswordHash,
        created_at: datetime,
        updated_at: datetime,
    ) -> User:
        """Reconstruye desde estado persistido."""
        return cls(
            id=id,
            email=email,
            password_hash=password_hash,
            created_at=created_at,
            updated_at=updated_at,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def email(self) -> Email:
        return self._email

    @property
    def password_hash(self) -> PasswordHash:
        return self._password_hash

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def change_password(self, password_hash: PasswordHash, at: datetime) -> None:
        self._password_hash = password_hash
        self._updated_at = at
