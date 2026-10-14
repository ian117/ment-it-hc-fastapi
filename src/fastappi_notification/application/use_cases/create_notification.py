from __future__ import annotations

from uuid import UUID

from fastappi_notification.application.channel_gateway_registry import ChannelGatewayRegistry
from fastappi_notification.application.deliver_notification import DeliverNotification
from fastappi_notification.application.ports import Clock, IdGenerator
from fastappi_notification.domain.channels import ChannelDraft, ChannelPolicyRegistry
from fastappi_notification.domain.notification import Notification


class CreateNotification:
    def __init__(
        self,
        policies: ChannelPolicyRegistry,
        gateways: ChannelGatewayRegistry,
        ids: IdGenerator,
        clock: Clock,
        deliver: DeliverNotification,
    ) -> None:
        self._policies = policies
        self._gateways = gateways
        self._ids = ids
        self._clock = clock
        self._deliver = deliver

    def execute(
        self,
        *,
        owner_id: UUID,
        title: str,
        content: str,
        channel: str,
        recipient: str,
    ) -> Notification:
        # 1-2: UnknownChannel / ChannelRuleViolation salen antes de escribir nada.
        policy = self._policies.policy(channel)
        self._gateways.gateway(channel)
        message = policy.prepare(ChannelDraft(title=title, content=content, recipient=recipient))

        notification = Notification.create(
            id=self._ids.new_id(),
            owner_id=owner_id,
            title=title,
            content=content,
            channel=channel,
            recipient=recipient,
            now=self._clock.now(),
        )
        return self._deliver.run(notification, message)
