from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastappi_notification.domain.email import Email
from fastappi_notification.domain.password_hash import PasswordHash
from fastappi_notification.domain.password_reset_token import PasswordResetToken
from fastappi_notification.domain.user import User
from fastappi_notification.infrastructure.persistence import (
    PasswordResetTokenModel,
    ResetTokenMapper,
    UserMapper,
    UserModel,
)

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
USER_ID = UUID("aaaaaaaa-0000-0000-0000-000000000001")
TOKEN_ID = UUID("bbbbbbbb-0000-0000-0000-000000000001")


def test_user_round_trip():
    user = User.create(id=USER_ID, email=Email.create("Ana@Example.com"), password_hash=PasswordHash("h"), now=NOW)
    model = UserMapper.to_model(user)
    assert isinstance(model, UserModel)
    assert (model.id, model.email, model.password_hash) == (USER_ID, "ana@example.com", "h")
    assert (model.created_at, model.updated_at) == (NOW, NOW)

    restored = UserMapper.to_domain(model)
    assert restored.id == USER_ID
    assert restored.email == Email("ana@example.com")
    assert restored.password_hash == PasswordHash("h")
    assert (restored.created_at, restored.updated_at) == (NOW, NOW)


def test_reset_token_round_trip_keeps_used_at():
    token = PasswordResetToken.create(
        id=TOKEN_ID, user_id=USER_ID, token_hash="a" * 64, expires_at=NOW + timedelta(minutes=15), now=NOW
    )
    model = ResetTokenMapper.to_model(token)
    assert isinstance(model, PasswordResetTokenModel)
    assert model.used_at is None and model.token_hash == "a" * 64

    token.mark_used(NOW + timedelta(minutes=1))
    restored = ResetTokenMapper.to_domain(ResetTokenMapper.to_model(token))
    assert restored.used_at == NOW + timedelta(minutes=1)
    assert (restored.id, restored.user_id, restored.expires_at) == (TOKEN_ID, USER_ID, NOW + timedelta(minutes=15))
