"""Fakes en memoria de los puertos de auth (ADR-013). Sin framework ni base de datos."""

from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass
from typing import Callable, Optional
from uuid import UUID

from fastappi_notification.application.ports import GeneratedResetToken, IssuedToken
from fastappi_notification.application.use_cases.confirm_password_reset import ConfirmPasswordReset
from fastappi_notification.application.use_cases.get_current_user import GetCurrentUser
from fastappi_notification.application.use_cases.login import Login
from fastappi_notification.application.use_cases.register_user import RegisterUser
from fastappi_notification.application.use_cases.request_password_reset import RequestPasswordReset
from fastappi_notification.domain.email import Email
from fastappi_notification.domain.errors import EmailAlreadyRegistered
from fastappi_notification.domain.password_hash import PasswordHash
from fastappi_notification.domain.password_reset_token import PasswordResetToken
from fastappi_notification.domain.user import User
from tests.application.fakes import FakeClock, SequentialIdGenerator

EMAIL = "ana@example.com"
PASSWORD = "correct-horse-battery"
NEW_PASSWORD = "brand-new-password"


class InMemoryUserRepository:
    """Guarda copias. `save` de un usuario NUEVO con email ya usado lanza
    `EmailAlreadyRegistered`, como la restricción única de la base."""

    def __init__(self) -> None:
        self._items: dict[UUID, User] = {}
        self.saves = 0

    def save(self, user: User) -> None:
        if user.id not in self._items and any(
            u.email == user.email for u in self._items.values()
        ):
            raise EmailAlreadyRegistered()
        self._items[user.id] = copy.deepcopy(user)
        self.saves += 1

    def find_by_email(self, email: Email) -> Optional[User]:
        for user in self._items.values():
            if user.email == email:
                return copy.deepcopy(user)
        return None

    def find_by_id(self, id: UUID) -> Optional[User]:
        stored = self._items.get(id)
        return copy.deepcopy(stored) if stored is not None else None

    # -- ayudas de test --
    def is_empty(self) -> bool:
        return not self._items

    def stored(self, id: UUID) -> User:
        return self._items[id]

    def insert_directly(self, user: User) -> None:
        """Simula que otro proceso insertó el usuario sin pasar por este repo."""
        self._items[user.id] = copy.deepcopy(user)


class InMemoryResetTokenRepository:
    """`consume` es atómico: `False` si el token almacenado ya estaba usado.

    `before_consume` (opcional) corre justo antes de consumir y permite simular que
    otro proceso ganó la carrera.
    """

    def __init__(self) -> None:
        self._items: dict[UUID, PasswordResetToken] = {}
        self.before_consume: Optional[Callable[[], None]] = None

    def save(self, token: PasswordResetToken) -> None:
        self._items[token.id] = copy.deepcopy(token)

    def find_by_hash(self, token_hash: str) -> Optional[PasswordResetToken]:
        for token in self._items.values():
            if token.token_hash == token_hash:
                return copy.deepcopy(token)
        return None

    def consume(self, token: PasswordResetToken) -> bool:
        if self.before_consume is not None:
            self.before_consume()
        stored = self._items.get(token.id)
        if stored is None or stored.used_at is not None or token.used_at is None:
            return False
        self._items[token.id] = copy.deepcopy(token)
        return True

    # -- ayudas de test --
    def is_empty(self) -> bool:
        return not self._items

    def all(self) -> list[PasswordResetToken]:
        return list(self._items.values())

    def stored(self, id: UUID) -> PasswordResetToken:
        return self._items[id]


class FakePasswordHasher:
    PREFIX = "hashed:"

    def __init__(self) -> None:
        self.verify_calls = 0
        self.hash_calls: list[str] = []

    def hash(self, plain: str) -> PasswordHash:
        self.hash_calls.append(plain)
        return PasswordHash(self.PREFIX + plain)

    def verify(self, plain: str, hash: PasswordHash) -> bool:
        self.verify_calls += 1
        return hash.value == self.PREFIX + plain


class FakeTokenIssuer:
    def issue(self, user_id: UUID) -> IssuedToken:
        return IssuedToken(access_token=f"token-for-{user_id}", expires_in=3600)


class FakeResetTokenGenerator:
    """Tokens `reset-token-1`, `reset-token-2`, ...; el hash es sha256 hex determinista."""

    def __init__(self) -> None:
        self._n = 0

    def generate(self) -> GeneratedResetToken:
        self._n += 1
        token = f"reset-token-{self._n}"
        return GeneratedResetToken(token=token, token_hash=self.hash(token))

    def hash(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()


@dataclass
class AuthWorld:
    """Cableado completo de los casos de uso de auth con fakes."""

    ttl_minutes: int = 15

    def __post_init__(self) -> None:
        self.users = InMemoryUserRepository()
        self.reset_tokens = InMemoryResetTokenRepository()
        self.hasher = FakePasswordHasher()
        self.issuer = FakeTokenIssuer()
        self.generator = FakeResetTokenGenerator()
        self.clock = FakeClock()
        self.ids = SequentialIdGenerator()
        self.register = RegisterUser(self.users, self.hasher, self.ids, self.clock)
        self.login = Login(self.users, self.hasher, self.issuer)
        self.get_current_user = GetCurrentUser(self.users)
        self.request_reset = RequestPasswordReset(
            self.users,
            self.reset_tokens,
            self.generator,
            self.ids,
            self.clock,
            self.ttl_minutes,
        )
        self.confirm_reset = ConfirmPasswordReset(
            self.users, self.reset_tokens, self.hasher, self.generator, self.clock
        )

    def registered_user(self, email: str = EMAIL, password: str = PASSWORD) -> User:
        return self.register.execute(email=email, password=password)
