"""Adaptador SQLAlchemy del puerto `ResetTokenRepository`. Cada operación es una transacción corta."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ...domain.password_reset_token import PasswordResetToken
from .reset_token_mapper import ResetTokenMapper
from .reset_token_model import PasswordResetTokenModel


class SqlAlchemyResetTokenRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, token: PasswordResetToken) -> None:
        try:
            self._session.add(ResetTokenMapper.to_model(token))
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

    def find_by_hash(self, token_hash: str) -> Optional[PasswordResetToken]:
        model = self._session.scalar(
            select(PasswordResetTokenModel).where(PasswordResetTokenModel.token_hash == token_hash)
        )
        return None if model is None else ResetTokenMapper.to_domain(model)

    def consume(self, token: PasswordResetToken) -> bool:
        """`UPDATE ... WHERE id AND used_at IS NULL`: cierra la carrera de doble uso."""
        if token.used_at is None:
            raise ValueError("consume requires a token already marked as used")
        try:
            result = self._session.execute(
                update(PasswordResetTokenModel)
                .where(
                    PasswordResetTokenModel.id == token.id,
                    PasswordResetTokenModel.used_at.is_(None),
                )
                .values(used_at=token.used_at)
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        return result.rowcount == 1
