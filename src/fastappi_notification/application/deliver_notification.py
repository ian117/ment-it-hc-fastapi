"""Servicio interno compartido por Create y Revise: el "mismo final" del flujo 3.3.

guardar `pending` -> entregar (sin transacción abierta, ADR-008) -> marcar -> guardar.
"""

from __future__ import annotations

from fastappi_notification.application.channel_gateway_registry import ChannelGatewayRegistry
from fastappi_notification.application.ports import DeliveryResult, NotificationRepository
from fastappi_notification.domain.channels import OutboundMessage
from fastappi_notification.domain.notification import Notification

_DEFAULT_FAILURE = "Delivery failed"


class DeliverNotification:
    def __init__(self, repo: NotificationRepository, gateways: ChannelGatewayRegistry) -> None:
        self._repo = repo
        self._gateways = gateways

    def run(self, notification: Notification, message: OutboundMessage) -> Notification:
        # Se resuelve antes de escribir: un canal sin gateway no debe dejar un `pending` huérfano.
        gateway = self._gateways.gateway(notification.channel)

        self._repo.save(notification)  # pending

        try:
            result = gateway.deliver(message)
        except Exception as exc:  # noqa: BLE001 - un gateway que lanza cuenta como entrega fallida (ADR-011)
            # Sin Clock en este servicio: `updated_at` ya es la hora de este intento.
            result = DeliveryResult(ok=False, at=notification.updated_at, detail=str(exc))

        if result.ok:
            notification.mark_sent(result.at)
        else:
            notification.mark_failed(result.detail or _DEFAULT_FAILURE, result.at)

        self._repo.save(notification)
        return notification
