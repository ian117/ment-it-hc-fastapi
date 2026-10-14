"""Adaptador SQLAlchemy del puerto `UserRepository`. Cada `save` es una transacción corta (ADR-014)."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...domain.email import Email
from ...domain.errors import EmailAlreadyRegistered
from ...domain.user import User
from .user_mapper import UserMapper
from .user_model import UserModel

UNIQUE_VIOLATION = "23505"


class SqlAlchemyUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, user: User) -> None:
        try:
            self._session.merge(UserMapper.to_model(user))
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            # La unicidad del email la garantiza la base, no un chequeo previo.
            if getattr(exc.orig, "sqlstate", None) == UNIQUE_VIOLATION:
                raise EmailAlreadyRegistered() from None
            raise
        except Exception:
            self._session.rollback()
            raise

    def find_by_email(self, email: Email) -> Optional[User]:
        model = self._session.scalar(select(UserModel).where(UserModel.email == email.value))
        return None if model is None else UserMapper.to_domain(model)

    def find_by_id(self, id: UUID) -> Optional[User]:
        model = self._session.get(UserModel, id)
        return None if model is None else UserMapper.to_domain(model)
