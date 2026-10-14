import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base


class User(Base):
    __tablename__ = "users"

    # Auth heredado (hasta F6/F7): el UUID se genera aquí; pasará al dominio en F6.
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # unique a nivel de base: es la única garantía real de unicidad ante dos
    # registros concurrentes (criterio 1). Un chequeo en código deja una
    # ventana entre el SELECT y el INSERT.
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # `default` (no server_default): la migración F4 quitó el DEFAULT de la columna,
    # así que el INSERT debe enviar el valor.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )
