"""Despachador de notificaciones.

Concentra el **orden invariante** del envío: validar → persistir en pendiente →
entregar → registrar el resultado. Los canales no participan de este orden ni
saben de la base; por eso un canal no puede registrar un envío que nunca se
validó. Sumar un canal no toca este archivo: se resuelve por nombre contra el
registry, sin un solo `if canal == ...`.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..channels import DeliveryResult, NotificationDraft, get_channel
from ..core.errors import AppError
from ..models import Notification, NotificationStatus, User
from ..schemas.notification import NotificationCreate, NotificationUpdate

logger = logging.getLogger("fastappi_notification")

MAX_PAGE_SIZE = 100


def create_and_send(db: Session, user: User, data: NotificationCreate) -> Notification:
    channel = get_channel(data.channel)
    draft = NotificationDraft(title=data.title, content=data.content, payload=data.payload)

    # Validación específica del canal ANTES de tocar la base. Si falla, propaga
    # ChannelValidationError -> 400 y no se escribió nada (criterio 2).
    message = channel.validate(draft)

    notification = Notification(
        user_id=user.id,
        title=data.title,
        content=data.content,
        channel=data.channel,
        payload=data.payload,
        status=NotificationStatus.pending.value,
    )
    db.add(notification)
    db.flush()

    # El envío es simulado y en memoria, así que va dentro de la misma
    # transacción. Límite conocido (documentado en el README): con un proveedor
    # real no se sostiene una transacción abierta sobre una llamada de red;
    # ahí corresponde commitear en 'pending' y actualizar el estado después.
    try:
        result = channel.deliver(message)
    except Exception as exc:  # noqa: BLE001 - un canal roto no debe tumbar el request
        logger.exception("Unexpected delivery error for channel %s", data.channel)
        result = DeliveryResult(success=False, error=f"unexpected error: {exc}")

    if result.success:
        notification.status = NotificationStatus.sent.value
        notification.sent_at = datetime.now(timezone.utc)
    else:
        # Un envío fallido nunca deja cero diagnóstico: motivo persistido y
        # logueado (criterio 12).
        notification.status = NotificationStatus.failed.value
        notification.error_message = result.error
        logger.error("Delivery failed for notification (channel=%s): %s", data.channel, result.error)

    db.commit()
    db.refresh(notification)
    return notification


def get_owned(db: Session, user: User, notification_id: int) -> Notification:
    # Filtra por id Y dueño en la misma consulta: "no existe" y "no es tuyo" son
    # indistinguibles desde afuera, así un 404 no confirma la existencia de un
    # recurso ajeno (criterio 5).
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
        )
    )
    if notification is None:
        raise AppError(404, "Notification not found", "not_found")
    return notification


def list_owned(db: Session, user: User, page: int, limit: int) -> tuple[list[Notification], int]:
    limit = min(limit, MAX_PAGE_SIZE)  # techo de tamaño de página (criterio 10)
    offset = (page - 1) * limit

    stmt = (
        select(Notification)
        .where(Notification.user_id == user.id)
        # Orden determinístico: más nuevas primero, con id como desempate para
        # que dos notificaciones del mismo instante tengan orden estable.
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items = list(db.scalars(stmt).all())
    total = db.scalar(
        select(func.count()).select_from(Notification).where(Notification.user_id == user.id)
    )
    return items, total


def update(db: Session, user: User, notification_id: int, data: NotificationUpdate) -> Notification:
    notification = get_owned(db, user, notification_id)

    title = data.title if data.title is not None else notification.title
    content = data.content if data.content is not None else notification.content
    channel_name = data.channel if data.channel is not None else notification.channel
    payload = data.payload if data.payload is not None else notification.payload

    # Re-validar contra el canal resultante: editar no puede dejar la
    # notificación violando las reglas del canal (p. ej. estirar un SMS más
    # allá de 160). No se reenvía: el envío ocurre solo al crear.
    channel = get_channel(channel_name)
    channel.validate(NotificationDraft(title=title, content=content, payload=payload))

    notification.title = title
    notification.content = content
    notification.channel = channel_name
    notification.payload = payload
    db.commit()
    db.refresh(notification)
    return notification


def delete(db: Session, user: User, notification_id: int) -> None:
    notification = get_owned(db, user, notification_id)
    db.delete(notification)
    db.commit()
