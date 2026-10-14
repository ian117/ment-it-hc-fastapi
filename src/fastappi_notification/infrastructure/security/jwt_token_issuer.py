"""Emisión y verificación de JWT de acceso (PyJWT, HS256). ADR-014.

Claims: `sub` (UUID del usuario), `iat`, `exp`, `type: "access"`. Sin email en el token.
La verificación es sin estado: no consulta la base.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Optional
from uuid import UUID

import jwt

from ...application.ports import Clock, IssuedToken

TOKEN_TYPE = "access"


class JwtTokenIssuer:
    def __init__(self, secret: str, algorithm: str, expires_in_seconds: int, clock: Clock) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._expires_in = expires_in_seconds
        self._clock = clock

    def issue(self, user_id: UUID) -> IssuedToken:
        now = self._clock.now()
        payload = {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(seconds=self._expires_in),
            "type": TOKEN_TYPE,
        }
        token = jwt.encode(payload, self._secret, algorithm=self._algorithm)
        return IssuedToken(access_token=token, expires_in=self._expires_in)


class JwtTokenVerifier:
    def __init__(self, secret: str, algorithm: str) -> None:
        self._secret = secret
        self._algorithm = algorithm

    def verify(self, token: str) -> Optional[UUID]:
        """UUID del usuario si firma, expiración, `type` y `sub` son válidos; `None` si no."""
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                options={"require": ["exp", "iat", "sub"]},
            )
            if payload.get("type") != TOKEN_TYPE:
                return None
            return UUID(str(payload["sub"]))
        except (jwt.PyJWTError, ValueError):
            return None
