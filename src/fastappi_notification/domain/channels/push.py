from __future__ import annotations

import re

from fastappi_notification.domain.channels.policy import ChannelDraft, OutboundMessage
from fastappi_notification.domain.errors import ChannelRuleViolation

_TOKEN_RE = re.compile(r"[A-Za-z0-9:_.\-]{8,4096}")


class PushPolicy:
    channel = "push"

    def prepare(self, draft: ChannelDraft) -> OutboundMessage:
        if _TOKEN_RE.fullmatch(draft.recipient) is None:
            raise ChannelRuleViolation(
                [
                    {
                        "field": "payload.recipient",
                        "message": "must be a device token of 8 to 4096 characters (letters, digits, ':', '_', '.', '-')",
                    }
                ]
            )
        return OutboundMessage(
            channel=self.channel,
            recipient=draft.recipient,
            subject=None,
            body=draft.content,
            html=None,
            data={"title": draft.title, "body": draft.content},
        )
