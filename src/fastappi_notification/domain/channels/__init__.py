"""Políticas de canal (ADR-005, ADR-010). Dominio puro: sin I/O ni dependencias externas."""

from fastappi_notification.domain.channels.email import EmailPolicy
from fastappi_notification.domain.channels.policy import (
    ChannelDraft,
    ChannelPolicy,
    OutboundMessage,
)
from fastappi_notification.domain.channels.push import PushPolicy
from fastappi_notification.domain.channels.registry import ChannelPolicyRegistry
from fastappi_notification.domain.channels.sms import SmsPolicy

__all__ = [
    "ChannelDraft",
    "ChannelPolicy",
    "ChannelPolicyRegistry",
    "EmailPolicy",
    "OutboundMessage",
    "PushPolicy",
    "SmsPolicy",
]
