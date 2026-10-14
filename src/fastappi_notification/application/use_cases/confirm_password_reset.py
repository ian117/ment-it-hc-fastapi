from __future__ import annotations

from fastappi_notification.application.ports import (
    Clock,
    PasswordHasher,
    ResetTokenGenerator,
    ResetTokenRepository,
    UserRepository,
)
from fastappi_notification.domain.errors import InvalidResetToken


class ConfirmPasswordReset:
    def __init__(
        self,
        users: UserRepository,
        reset_tokens: ResetTokenRepository,
        hasher: PasswordHasher,
        generator: ResetTokenGenerator,
        clock: Clock,
    ) -> None:
        self._users = users
        self._reset_tokens = reset_tokens
        self._hasher = hasher
        self._generator = generator
        self._clock = clock

    def execute(self, *, token: str, new_password: str) -> None:
        reset = self._reset_tokens.find_by_hash(self._generator.hash(token))
        if reset is None:
            raise InvalidResetToken()
        now = self._clock.now()
        reset.mark_used(now)  # InvalidResetToken si está vencido o usado; no muta
        user = self._users.find_by_id(reset.user_id)
        if user is None:
            raise InvalidResetToken()
        new_hash = self._hasher.hash(new_password)
        # Quema el token antes de cambiar la contraseña (falla del lado seguro).
        if not self._reset_tokens.consume(reset):
            raise InvalidResetToken()
        user.change_password(new_hash, now)
        self._users.save(user)
