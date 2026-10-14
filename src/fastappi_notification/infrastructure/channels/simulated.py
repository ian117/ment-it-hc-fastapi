"""Base de los gateways simulados (ADR-012): fallo determinista, sin I/O real."""

from __future__ import annotations

import logging

from ...application.ports import Clock, DeliveryResult
from ...domain.channels import OutboundMessage

logger = logging.getLogger("fastappi_notification.channels")

FAILURE_DETAIL = "Simulated delivery failure"


class SimulatedGateway:
    channel: str

    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    def _fails(self, message: OutboundMessage) -> bool:
        raise NotImplementedError

    def deliver(self, message: OutboundMessage) -> DeliveryResult:
        failed = self._fails(message)
        result = DeliveryResult(
            ok=not failed,
            at=self._clock.now(),
            detail=FAILURE_DETAIL if failed else None,
        )
        logger.info(
            "delivery channel=%s recipient=%s result=%s",
            self.channel,
            message.recipient,
            "failed" if failed else "sent",
        )
        return result
