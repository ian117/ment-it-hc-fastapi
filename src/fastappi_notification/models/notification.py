import enum
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db import Base


class NotificationStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # `channel` queda como texto libre a propósito: NO lleva un CHECK ni un tipo
    # ENUM de Postgres. La lista de canales válidos vive en el registry de la
    # capa de aplicación, así sumar un canal (WhatsApp) no toca la base ni exige
    # una migración. La contrapartida está documentada en el README.
    channel: Mapped[str] = mapped_column(String(32), nullable=False)

    # Datos específicos del canal (email destinatario, número, device token…).
    # JSONB mantiene el esquema agnóstico del canal: sumar un canal con otros
    # campos no altera la tabla.
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=NotificationStatus.pending.value
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="notifications")  # noqa: F821

    __table_args__ = (
        # El conjunto de estados sí es cerrado y controlado por la app, así que
        # un CHECK acá es integridad barata sin costo de extensibilidad.
        CheckConstraint(
            "status IN ('pending', 'sent', 'failed')",
            name="ck_notifications_status",
        ),
    )
