from __future__ import annotations

import re

from fastappi_notification.domain.channels.policy import ChannelDraft, OutboundMessage
from fastappi_notification.domain.errors import ChannelRuleViolation

# [0-9] y no \d: en Python \d acepta dígitos Unicode.
_E164_RE = re.compile(r"\+[1-9][0-9]{1,14}")
_MAX_CONTENT = 160  # code points (len de str en Python)


class SmsPolicy:
    channel = "sms"

    def prepare(self, draft: ChannelDraft) -> OutboundMessage:
        violations: list[dict[str, str]] = []
        if _E164_RE.fullmatch(draft.recipient) is None:
            violations.append(
                {"field": "payload.recipient", "message": "must be a phone number in E.164 format (e.g. +5219611234567)"}
            )
        if len(draft.content) > _MAX_CONTENT:
            violations.append({"field": "content", "message": "must be at most 160 characters for sms"})
        if violations:
            raise ChannelRuleViolation(violations)
        return OutboundMessage(
            channel=self.channel,
            recipient=draft.recipient,
            subject=None,
            body=draft.content,
            html=None,
            data=None,
        )
