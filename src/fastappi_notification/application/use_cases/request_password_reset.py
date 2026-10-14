from __future__ import annotations

from datetime import timedelta
from typing import Optional

from fastappi_notification.application.ports import (
    Clock,
    IdGenerator,
    ResetTokenGenerator,
    ResetTokenRepository,
    UserRepository,
)
from fastappi_notification.domain.email import Email
from fastappi_notification.domain.password_reset_token import PasswordResetToken


class RequestPasswordReset:
    def __init__(
        self,
        users: UserRepository,
        reset_tokens: ResetTokenRepository,
        generator: ResetTokenGenerator,
        ids: IdGenerator,
        clock: Clock,
        ttl_minutes: int = 15,
    ) -> None:
        self._users = users
        self._reset_tokens = reset_tokens
        self._generator = generator
        self._ids = ids
        self._clock = clock
        self._ttl = timedelta(minutes=ttl_minutes)

    def execute(self, *, email: str) -> Optional[str]:
        """Token en claro si el usuario existe; `None` si no. Qué se expone es de `api/`."""
        user = self._users.find_by_email(Email.create(email))  # InvalidEmail
        if user is None:
            return None
        now = self._clock.now()
        generated = self._generator.generate()
        self._reset_tokens.save(
            PasswordResetToken.create(
                id=self._ids.new_id(),
                user_id=user.id,
                token_hash=generated.token_hash,
                expires_at=now + self._ttl,
                now=now,
            )
        )
        return generated.token
