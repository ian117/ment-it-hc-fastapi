from __future__ import annotations

from typing import Optional

from fastappi_notification.application.ports import IssuedToken, PasswordHasher, TokenIssuer, UserRepository
from fastappi_notification.domain.email import Email
from fastappi_notification.domain.errors import InvalidCredentials, InvalidEmail
from fastappi_notification.domain.password_hash import PasswordHash

_DECOY_PLAIN = "decoy-password-for-timing-equalization"


class Login:
    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        tokens: TokenIssuer,
        decoy: Optional[PasswordHash] = None,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens
        # Si la composición crea un `Login` por request, debe pasar un señuelo ya hecho:
        # si no, cada instancia hashearía uno propio y el tiempo delataría el email.
        self._decoy = decoy

    def execute(self, *, email: str, password: str) -> IssuedToken:
        user = None
        try:
            user = self._users.find_by_email(Email.create(email))
        except InvalidEmail:
            pass  # indistinguible de "no existe"

        if user is None:
            # Verifica igual contra un señuelo para no filtrar por timing.
            self._hasher.verify(password, self._decoy_hash())
            raise InvalidCredentials()
        if not self._hasher.verify(password, user.password_hash):
            raise InvalidCredentials()
        return self._tokens.issue(user.id)

    def _decoy_hash(self) -> PasswordHash:
        if self._decoy is None:
            self._decoy = self._hasher.hash(_DECOY_PLAIN)
        return self._decoy
