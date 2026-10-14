from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastappi_notification.domain.email import Email
from fastappi_notification.domain.password_hash import PasswordHash
from fastappi_notification.domain.user import User

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
T1 = T0 + timedelta(minutes=5)


def crear() -> User:
    return User.create(
        id=uuid4(), email=Email.create("ana@example.com"), password_hash=PasswordHash("h1"), now=T0
    )


def test_create_fija_created_y_updated_a_now():
    user = crear()
    assert user.created_at == T0
    assert user.updated_at == T0
    assert user.email.value == "ana@example.com"
    assert user.password_hash == PasswordHash("h1")


def test_change_password_cambia_hash_y_updated_at():
    user = crear()
    user.change_password(PasswordHash("h2"), T1)
    assert user.password_hash == PasswordHash("h2")
    assert user.updated_at == T1
    assert user.created_at == T0


def test_restore_reconstruye_sin_modificar():
    original = crear()
    restored = User.restore(
        id=original.id,
        email=original.email,
        password_hash=original.password_hash,
        created_at=T0,
        updated_at=T1,
    )
    assert restored.id == original.id
    assert restored.updated_at == T1
