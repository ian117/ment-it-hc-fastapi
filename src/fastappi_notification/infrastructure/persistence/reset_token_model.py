"""Modelo SQLAlchemy de `password_reset_tokens`. Solo guarda el hash del token, nunca el token en claro."""

import uuid
from datetime import datetime

from sqlalchemy import CHAR, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db import Base


class PasswordResetTokenModel(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # sha256 en hexadecimal: siempre 64 caracteres.
    token_hash: Mapped[str] = mapped_column(CHAR(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
