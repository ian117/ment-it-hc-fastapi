"""Registro de gateways por canal; análogo a `ChannelPolicyRegistry` del dominio (ADR-011)."""

from __future__ import annotations

from typing import Iterable

from fastappi_notification.application.ports import ChannelGateway
from fastappi_notification.domain.errors import UnknownChannel


class ChannelGatewayRegistry:
    def __init__(self, gateways: Iterable[ChannelGateway]) -> None:
        self._gateways: dict[str, ChannelGateway] = {}
        for gateway in gateways:
            if gateway.channel in self._gateways:
                raise ValueError(f"Duplicate channel gateway: {gateway.channel}")
            self._gateways[gateway.channel] = gateway

    def gateway(self, channel: str) -> ChannelGateway:
        try:
            return self._gateways[channel]
        except KeyError:
            raise UnknownChannel(channel) from None

    def has(self, channel: str) -> bool:
        return channel in self._gateways
