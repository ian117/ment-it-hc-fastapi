"""Traduce `UserModel` <-> `User` (dominio)."""

from __future__ import annotations

from datetime import timezone

from ...domain.email import Email
from ...domain.password_hash import PasswordHash
from ...domain.user import User
from .user_model import UserModel


class UserMapper:
    @staticmethod
    def to_domain(model: UserModel) -> User:
        return User.restore(
            id=model.id,
            # Estado persistido: ya fue normalizado al registrarse, no se revalida.
            email=Email(model.email),
            password_hash=PasswordHash(model.password_hash),
            created_at=model.created_at.astimezone(timezone.utc),
            updated_at=model.updated_at.astimezone(timezone.utc),
        )

    @staticmethod
    def to_model(user: User) -> UserModel:
        return UserModel(
            id=user.id,
            email=user.email.value,
            password_hash=user.password_hash.value,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
