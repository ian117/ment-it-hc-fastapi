"""Puertos de la capa de aplicación (ADR-011). Solo stdlib + dominio.

Las implementaciones (SQLAlchemy, gateways simulados, reloj del sistema) viven en
`infrastructure/` y se conectan en la raíz de composición.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol
from uuid import UUID

from fastappi_notification.domain.channels import OutboundMessage
from fastappi_notification.domain.email import Email
from fastappi_notification.domain.notification import Notification
from fastappi_notification.domain.password_hash import PasswordHash
from fastappi_notification.domain.password_reset_token import PasswordResetToken
from fastappi_notification.domain.user import User


@dataclass(frozen=True)
class DeliveryResult:
    ok: bool
    at: datetime
    detail: Optional[str] = None


class NotificationRepository(Protocol):
    def save(self, notification: Notification) -> None:
        """Inserta o actualiza (upsert por `id`)."""
        ...

    def find_by_id(self, id: UUID, owner_id: UUID) -> Optional[Notification]:
        """`None` si no existe **o** no pertenece a `owner_id`."""
        ...

    def list_by_owner(
        self, owner_id: UUID, page: int, limit: int
    ) -> tuple[list[Notification], int]:
        """Página (1-based) de las notificaciones del dueño, `created_at desc, id desc`,
        y el total sin paginar."""
        ...

    def delete(self, id: UUID, owner_id: UUID) -> bool:
        """`False` si no existe o no pertenece a `owner_id`."""
        ...


class ChannelGateway(Protocol):
    channel: str

    def deliver(self, message: OutboundMessage) -> DeliveryResult: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new_id(self) -> UUID: ...


# -- Auth (ADR-013) ---------------------------------------------------------


@dataclass(frozen=True)
class IssuedToken:
    access_token: str
    expires_in: int  # segundos; `tokenType: "Bearer"` es del contrato HTTP, no del puerto


@dataclass(frozen=True)
class GeneratedResetToken:
    token: str  # en claro, de alta entropía; nunca se persiste
    token_hash: str  # sha256 hex de 64 caracteres


class UserRepository(Protocol):
    def save(self, user: User) -> None:
        """Inserta o actualiza (upsert por `id`). Insertar un usuario nuevo con email ya
        usado lanza `EmailAlreadyRegistered` (la unicidad la garantiza la base)."""
        ...

    def find_by_email(self, email: Email) -> Optional[User]: ...

    def find_by_id(self, id: UUID) -> Optional[User]: ...


class ResetTokenRepository(Protocol):
    def save(self, token: PasswordResetToken) -> None:
        """Inserta."""
        ...

    def find_by_hash(self, token_hash: str) -> Optional[PasswordResetToken]: ...

    def consume(self, token: PasswordResetToken) -> bool:
        """Persiste `used_at` solo si en la base sigue sin usar. `False` si otro lo
        consumió antes (`UPDATE ... WHERE used_at IS NULL`)."""
        ...


class PasswordHasher(Protocol):
    def hash(self, plain: str) -> PasswordHash: ...

    def verify(self, plain: str, hash: PasswordHash) -> bool: ...


class TokenIssuer(Protocol):
    def issue(self, user_id: UUID) -> IssuedToken: ...


class ResetTokenGenerator(Protocol):
    def generate(self) -> GeneratedResetToken: ...

    def hash(self, token: str) -> str:
        """sha256 hex del token en claro (el mismo algoritmo que usa `generate`)."""
        ...
