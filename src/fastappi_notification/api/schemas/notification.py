"""Esquemas HTTP de `/notifications` (contrato: camelCase, propiedades extra rechazadas)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from ...application.use_cases.list_my_notifications import ListResult
from ...domain.notification import Notification


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class StrictCamelModel(CamelModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class ChannelPayload(StrictCamelModel):
    recipient: str = Field(min_length=1)


class CreateNotificationRequest(StrictCamelModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    # Solo string: el registro de canales decide si existe (ADR-004, ADR-012).
    channel: str = Field(min_length=1, max_length=32)
    payload: ChannelPayload


class ReviseNotificationRequest(StrictCamelModel):
    """Todos opcionales; un `null` explícito se rechaza (el contrato no lo admite)."""

    # `default=None` sobre un tipo no opcional: ausente es válido, `null` no.
    title: str = Field(default=None, min_length=1, max_length=255)
    content: str = Field(default=None, min_length=1)
    payload: ChannelPayload = Field(default=None)

    @model_validator(mode="after")
    def _at_least_one(self) -> "ReviseNotificationRequest":
        if not self.model_fields_set:
            raise ValueError("at least one of title, content or payload is required")
        return self


class NotificationResponse(CamelModel):
    id: UUID
    title: str
    content: str
    channel: str
    payload: ChannelPayload
    status: str
    attempts: int
    error_message: Optional[str]
    sent_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, notification: Notification) -> "NotificationResponse":
        return cls(
            id=notification.id,
            title=notification.title,
            content=notification.content,
            channel=notification.channel,
            payload=ChannelPayload(recipient=notification.recipient),
            status=notification.status.value,
            attempts=notification.attempts,
            error_message=notification.error_message,
            sent_at=notification.sent_at,
            created_at=notification.created_at,
            updated_at=notification.updated_at,
        )


class NotificationPage(CamelModel):
    data: list[NotificationResponse]
    total: int
    page: int
    limit: int

    @classmethod
    def from_result(cls, result: ListResult) -> "NotificationPage":
        return cls(
            data=[NotificationResponse.from_domain(n) for n in result.data],
            total=result.total,
            page=result.page,
            limit=result.limit,
        )
