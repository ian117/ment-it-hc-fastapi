from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from fastappi_notification.api.schemas.notification import (
    CreateNotificationRequest,
    NotificationPage,
    NotificationResponse,
    ReviseNotificationRequest,
)
from fastappi_notification.application.use_cases.list_my_notifications import ListResult
from fastappi_notification.domain.notification import Notification

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def _notification() -> Notification:
    return Notification.create(
        id=UUID("11111111-0000-0000-0000-000000000001"),
        owner_id=UUID("aaaaaaaa-0000-0000-0000-000000000001"),
        title="t", content="c", channel="push", recipient="device-token-1", now=NOW,
    )


def test_create_request_rejects_unknown_properties():
    with pytest.raises(ValidationError):
        CreateNotificationRequest.model_validate(
            {"title": "t", "content": "c", "channel": "sms", "payload": {"recipient": "x"}, "extra": 1}
        )


def test_create_request_rejects_extra_payload_keys():
    with pytest.raises(ValidationError):
        CreateNotificationRequest.model_validate(
            {"title": "t", "content": "c", "channel": "sms", "payload": {"recipient": "x", "phone": "1"}}
        )


def test_create_request_accepts_any_channel_string():
    body = CreateNotificationRequest.model_validate(
        {"title": "t", "content": "c", "channel": "whatsapp", "payload": {"recipient": "x"}}
    )
    assert body.channel == "whatsapp"


@pytest.mark.parametrize("data", [{}, {"channel": "sms"}, {"title": None}, {"payload": {}}])
def test_revise_request_rejects_empty_channel_and_nulls(data):
    with pytest.raises(ValidationError):
        ReviseNotificationRequest.model_validate(data)


def test_revise_request_tracks_provided_fields():
    body = ReviseNotificationRequest.model_validate({"payload": {"recipient": "x"}})
    assert body.title is None
    assert body.payload.recipient == "x"


def test_response_is_camel_case_and_keeps_nulls_without_owner():
    dumped = NotificationResponse.from_domain(_notification()).model_dump(mode="json", by_alias=True)
    assert set(dumped) == {
        "id", "title", "content", "channel", "payload", "status", "attempts",
        "errorMessage", "sentAt", "createdAt", "updatedAt",
    }
    assert dumped["payload"] == {"recipient": "device-token-1"}
    assert dumped["errorMessage"] is None and dumped["sentAt"] is None
    assert dumped["status"] == "pending" and dumped["attempts"] == 0


def test_page_uses_data_key():
    page = NotificationPage.from_result(ListResult(data=[_notification()], total=1, page=1, limit=20))
    dumped = page.model_dump(mode="json", by_alias=True)
    assert set(dumped) == {"data", "total", "page", "limit"}
    assert len(dumped["data"]) == 1


@pytest.mark.parametrize("model", ["RegisterRequest", "LoginRequest", "PasswordResetRequest"])
def test_auth_requests_reject_email_with_surrounding_whitespace(model):
    from fastappi_notification.api.schemas import auth

    cls = getattr(auth, model)
    extra = {} if model == "PasswordResetRequest" else {"password": "secret12345"}
    with pytest.raises(ValidationError) as exc:
        cls.model_validate({"email": "  ana@example.com  ", **extra})
    assert exc.value.errors()[0]["loc"] == ("email",)
    cls.model_validate({"email": "ana@example.com", **extra})
