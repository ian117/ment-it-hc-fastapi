from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastappi_notification.application.deliver_notification import DeliverNotification
from fastappi_notification.application.ports import Clock, NotificationRepository
from fastappi_notification.domain.channels import ChannelDraft, ChannelPolicyRegistry
from fastappi_notification.domain.errors import NotificationNotFound
from fastappi_notification.domain.notification import Notification


class ReviseNotification:
    """Precedencia de errores (ADR-011): 404 -> 409 -> 400, y todo antes de mutar o guardar."""

    def __init__(
        self,
        repo: NotificationRepository,
        policies: ChannelPolicyRegistry,
        clock: Clock,
        deliver: DeliverNotification,
    ) -> None:
        self._repo = repo
        self._policies = policies
        self._clock = clock
        self._deliver = deliver

    def execute(
        self,
        owner_id: UUID,
        id: UUID,
        title: Optional[str] = None,
        content: Optional[str] = None,
        recipient: Optional[str] = None,
    ) -> Notification:
        notification = self._repo.find_by_id(id, owner_id)
        if notification is None:
            raise NotificationNotFound(id)

        notification.ensure_editable()  # 409

        # Datos fusionados: lo no enviado conserva el valor actual.
        draft = ChannelDraft(
            title=notification.title if title is None else title,
            content=notification.content if content is None else content,
            recipient=notification.recipient if recipient is None else recipient,
        )
        message = self._policies.policy(notification.channel).prepare(draft)  # 400

        notification.revise(self._clock.now(), title=title, content=content, recipient=recipient)
        return self._deliver.run(notification, message)
