"""Adaptador del puerto `PasswordHasher` con argon2 (pwdlib)."""

from __future__ import annotations

from pwdlib import PasswordHash as PwdlibPasswordHash

from ...domain.password_hash import PasswordHash


class Argon2PasswordHasher:
    def __init__(self) -> None:
        # `recommended()` deja lugar a migrar de esquema sin invalidar hashes viejos.
        self._hasher = PwdlibPasswordHash.recommended()

    def hash(self, plain: str) -> PasswordHash:
        return PasswordHash(self._hasher.hash(plain))

    def verify(self, plain: str, hash: PasswordHash) -> bool:
        return self._hasher.verify(plain, hash.value)
