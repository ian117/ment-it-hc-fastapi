from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastappi_notification.domain.notification import Notification, NotificationStatus
from fastappi_notification.infrastructure.persistence import NotificationMapper, NotificationModel

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
ID = UUID("11111111-0000-0000-0000-000000000001")
OWNER = UUID("aaaaaaaa-0000-0000-0000-000000000001")


def _failed() -> Notification:
    n = Notification.create(
        id=ID, owner_id=OWNER, title="t", content="c", channel="sms", recipient="+5219611234567", now=NOW
    )
    n.mark_failed("boom", NOW + timedelta(seconds=1))
    return n


def test_to_model_maps_every_column_and_wraps_recipient_in_payload():
    model = NotificationMapper.to_model(_failed())
    assert model.id == ID
    assert model.user_id == OWNER
    assert model.channel == "sms"
    assert model.payload == {"recipient": "+5219611234567"}
    assert model.status == "failed"
    assert model.attempts == 1
    assert model.error_message == "boom"
    assert model.sent_at is None
    assert model.created_at == NOW
    assert model.updated_at == NOW + timedelta(seconds=1)


def test_roundtrip_preserves_the_entity():
    original = _failed()
    restored = NotificationMapper.to_domain(NotificationMapper.to_model(original))
    for attr in (
        "id", "owner_id", "title", "content", "channel", "recipient",
        "status", "attempts", "error_message", "sent_at", "created_at", "updated_at",
    ):
        assert getattr(restored, attr) == getattr(original, attr), attr
    assert restored.status is NotificationStatus.FAILED


def test_to_domain_normalizes_timestamps_to_utc():
    tz = timezone(timedelta(hours=-6))
    model = NotificationModel(
        id=ID, user_id=OWNER, title="t", content="c", channel="email",
        payload={"recipient": "a@b.co"}, status="sent", attempts=1, error_message=None,
        sent_at=NOW.astimezone(tz), created_at=NOW.astimezone(tz), updated_at=NOW.astimezone(tz),
    )
    restored = NotificationMapper.to_domain(model)
    assert restored.sent_at.utcoffset() == timedelta(0)
    assert restored.sent_at == NOW
