"""Canales de envío.

Importar los módulos concretos ejecuta el decorador `@register` de cada uno y
puebla el registry. Cualquier código que importe `channels` obtiene el registry
ya completo. Sumar un canal nuevo = crear su módulo y agregar un import acá.
"""

from .base import (
    Channel,
    ChannelValidationError,
    DeliveryResult,
    NotificationDraft,
    ValidatedMessage,
    channel_names,
    get_channel,
    register,
)
from . import email, push, sms  # noqa: F401  (import con efecto: registra los canales)

__all__ = [
    "Channel",
    "ChannelValidationError",
    "DeliveryResult",
    "NotificationDraft",
    "ValidatedMessage",
    "channel_names",
    "get_channel",
    "register",
]
