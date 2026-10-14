"""Modelo SQLAlchemy de `users`. Nunca sale de `infrastructure/`: el mapper lo traduce al dominio."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db import Base


class UserModel(Base):
    __tablename__ = "users"

    # Id y timestamps los pone el dominio, no la base (ADR-014).
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    # unique a nivel de base: es la única garantía real de unicidad ante dos
    # registros concurrentes; el repositorio traduce la violación (SQLSTATE 23505).
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
