"""Contrato de política de canal: valida y formatea, sin hacer I/O (diseño 2.3, ADR-010)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass(frozen=True)
class ChannelDraft:
    title: str
    content: str
    recipient: str


@dataclass(frozen=True)
class OutboundMessage:
    channel: str
    recipient: str
    subject: Optional[str]
    body: str
    html: Optional[str]
    data: Optional[dict[str, str]]


class ChannelPolicy(Protocol):
    channel: str

    def prepare(self, draft: ChannelDraft) -> OutboundMessage:
        """Lanza `ChannelRuleViolation` si el borrador incumple las reglas del canal."""
        ...
