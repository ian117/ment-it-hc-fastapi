"""Entidad `PasswordResetToken` (diseño 2.1, ADR-013). Guarda solo el hash del token."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastappi_notification.domain.errors import InvalidResetToken


class PasswordResetToken:
    __slots__ = ("_id", "_user_id", "_token_hash", "_expires_at", "_used_at", "_created_at")

    def __init__(
        self,
        *,
        id: UUID,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        used_at: Optional[datetime],
        created_at: datetime,
    ) -> None:
        self._id = id
        self._user_id = user_id
        self._token_hash = token_hash
        self._expires_at = expires_at
        self._used_at = used_at
        self._created_at = created_at

    @classmethod
    def create(
        cls,
        *,
        id: UUID,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        now: datetime,
    ) -> PasswordResetToken:
        return cls(
            id=id,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            used_at=None,
            created_at=now,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: UUID,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        used_at: Optional[datetime],
        created_at: datetime,
    ) -> PasswordResetToken:
        """Reconstruye desde estado persistido."""
        return cls(
            id=id,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            used_at=used_at,
            created_at=created_at,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def user_id(self) -> UUID:
        return self._user_id

    @property
    def token_hash(self) -> str:
        return self._token_hash

    @property
    def expires_at(self) -> datetime:
        return self._expires_at

    @property
    def used_at(self) -> Optional[datetime]:
        return self._used_at

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def is_usable(self, at: datetime) -> bool:
        """Sin usar y no vencido (`expires_at > at`: en el instante exacto ya venció)."""
        return self._used_at is None and self._expires_at > at

    def mark_used(self, at: datetime) -> None:
        if not self.is_usable(at):
            raise InvalidResetToken()
        self._used_at = at
