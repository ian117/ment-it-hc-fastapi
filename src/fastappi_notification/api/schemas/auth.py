"""Esquemas HTTP de `/auth/*` (contrato: camelCase, propiedades extra rechazadas).

La política de longitud de contraseña vive solo aquí (ADR-013, ADR-014).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import EmailStr, Field

from ...domain.user import User
from .notification import CamelModel, StrictCamelModel


class RegisterRequest(StrictCamelModel):
    email: EmailStr = Field(max_length=320)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(StrictCamelModel):
    email: EmailStr
    password: str = Field(min_length=1)


class PasswordResetRequest(StrictCamelModel):
    email: EmailStr


class PasswordResetConfirm(StrictCamelModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class UserResponse(CamelModel):
    """Usuario público: sin hash por construcción (se serializa desde el dominio, no desde el ORM)."""

    id: UUID
    email: EmailStr
    created_at: datetime

    @classmethod
    def from_domain(cls, user: User) -> "UserResponse":
        return cls(id=user.id, email=user.email.value, created_at=user.created_at)


class AccessTokenResponse(CamelModel):
    access_token: str
    token_type: Literal["Bearer"]
    expires_in: int = Field(description="Segundos de vigencia")


class PasswordResetRequestedResponse(CamelModel):
    message: str
    # `default=None` sobre un tipo no opcional: ausente es válido y el schema publica solo `string`.
    reset_token: str = Field(default=None, description="Solo fuera de producción.")


class MessageResponse(CamelModel):
    message: str
