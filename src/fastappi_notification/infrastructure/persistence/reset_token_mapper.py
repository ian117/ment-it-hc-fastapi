"""Traduce `PasswordResetTokenModel` <-> `PasswordResetToken` (dominio)."""

from __future__ import annotations

from datetime import timezone

from ...domain.password_reset_token import PasswordResetToken
from .reset_token_model import PasswordResetTokenModel


class ResetTokenMapper:
    @staticmethod
    def to_domain(model: PasswordResetTokenModel) -> PasswordResetToken:
        return PasswordResetToken.restore(
            id=model.id,
            user_id=model.user_id,
            token_hash=model.token_hash,
            expires_at=model.expires_at.astimezone(timezone.utc),
            used_at=None if model.used_at is None else model.used_at.astimezone(timezone.utc),
            created_at=model.created_at.astimezone(timezone.utc),
        )

    @staticmethod
    def to_model(token: PasswordResetToken) -> PasswordResetTokenModel:
        return PasswordResetTokenModel(
            id=token.id,
            user_id=token.user_id,
            token_hash=token.token_hash,
            expires_at=token.expires_at,
            used_at=token.used_at,
            created_at=token.created_at,
        )
