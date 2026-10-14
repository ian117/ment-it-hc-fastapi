from __future__ import annotations

import html

from fastappi_notification.domain.channels.policy import ChannelDraft, OutboundMessage
from fastappi_notification.domain.email import EMAIL_PATTERN, MAX_EMAIL_LENGTH
from fastappi_notification.domain.errors import ChannelRuleViolation


class EmailPolicy:
    channel = "email"

    def prepare(self, draft: ChannelDraft) -> OutboundMessage:
        recipient = draft.recipient
        if len(recipient) > MAX_EMAIL_LENGTH or EMAIL_PATTERN.fullmatch(recipient) is None:
            raise ChannelRuleViolation(
                [{"field": "payload.recipient", "message": "must be a valid email address (max 320 characters)"}]
            )
        title = html.escape(draft.title, quote=True)
        content = html.escape(draft.content, quote=True)
        return OutboundMessage(
            channel=self.channel,
            recipient=recipient,
            subject=draft.title,
            body=draft.content,
            html=f"<h1>{title}</h1><p>{content}</p>",
            data=None,
        )
