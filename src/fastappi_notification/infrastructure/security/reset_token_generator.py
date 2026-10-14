"""Adaptador del puerto `ResetTokenGenerator`: token de alta entropía + sha256 hex."""

from __future__ import annotations

import hashlib
import secrets

from ...application.ports import GeneratedResetToken


class SecretsResetTokenGenerator:
    def generate(self) -> GeneratedResetToken:
        token = secrets.token_urlsafe(32)
        return GeneratedResetToken(token=token, token_hash=self.hash(token))

    def hash(self, token: str) -> str:
        # SHA-256 y no argon2: el token ya es aleatorio de alta entropía y necesitamos
        # un hash determinista para buscar por él en la base.
        return hashlib.sha256(token.encode()).hexdigest()
