"""Registro de políticas por canal. El conjunto válido de canales lo define la raíz de composición (ADR-004)."""

from __future__ import annotations

from typing import Iterable

from fastappi_notification.domain.channels.policy import ChannelPolicy
from fastappi_notification.domain.errors import UnknownChannel


class ChannelPolicyRegistry:
    def __init__(self, policies: Iterable[ChannelPolicy]) -> None:
        self._policies: dict[str, ChannelPolicy] = {}
        for policy in policies:
            if policy.channel in self._policies:
                raise ValueError(f"Duplicate channel policy: {policy.channel}")
            self._policies[policy.channel] = policy

    def policy(self, channel: str) -> ChannelPolicy:
        try:
            return self._policies[channel]
        except KeyError:
            raise UnknownChannel(channel) from None

    def has(self, channel: str) -> bool:
        return channel in self._policies

    def channels(self) -> list[str]:
        return list(self._policies)
