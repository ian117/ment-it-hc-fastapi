"""Repositorios de auth contra PostgreSQL real (esquema de Alembic)."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from fastappi_notification.domain.email import Email
from fastappi_notification.domain.errors import EmailAlreadyRegistered
from fastappi_notification.domain.password_hash import PasswordHash
from fastappi_notification.domain.password_reset_token import PasswordResetToken
from fastappi_notification.domain.user import User
from fastappi_notification.infrastructure.persistence import (
    SqlAlchemyResetTokenRepository,
    SqlAlchemyUserRepository,
)

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def _user(email: str | None = None) -> User:
    email = email or f"repo-{uuid4().hex[:10]}@example.com"
    return User.create(id=uuid4(), email=Email.create(email), password_hash=PasswordHash("h"), now=NOW)


def test_user_save_find_and_update(db_session):
    repo = SqlAlchemyUserRepository(db_session)
    user = _user()
    repo.save(user)

    assert repo.find_by_email(user.email).id == user.id
    assert repo.find_by_id(user.id).email == user.email
    assert repo.find_by_email(Email.create(" " + user.email.value.upper())).id == user.id
    assert repo.find_by_id(uuid4()) is None

    user.change_password(PasswordHash("new"), NOW + timedelta(minutes=1))
    repo.save(user)
    assert repo.find_by_id(user.id).password_hash == PasswordHash("new")
    assert repo.find_by_id(user.id).updated_at == NOW + timedelta(minutes=1)


def test_duplicate_email_is_translated_and_session_stays_usable(db_session):
    repo = SqlAlchemyUserRepository(db_session)
    first = _user()
    repo.save(first)

    with pytest.raises(EmailAlreadyRegistered):
        repo.save(_user(first.email.value))

    assert repo.find_by_id(first.id) is not None  # rollback hecho: la sesión sigue sirviendo


def test_consume_is_single_use(db_session):
    users = SqlAlchemyUserRepository(db_session)
    tokens = SqlAlchemyResetTokenRepository(db_session)
    user = _user()
    users.save(user)
    token = PasswordResetToken.create(
        id=uuid4(), user_id=user.id, token_hash=uuid4().hex + uuid4().hex, expires_at=NOW + timedelta(minutes=15), now=NOW
    )
    tokens.save(token)

    found = tokens.find_by_hash(token.token_hash)
    assert found.id == token.id and found.used_at is None
    assert tokens.find_by_hash("0" * 64) is None

    first = tokens.find_by_hash(token.token_hash)
    second = tokens.find_by_hash(token.token_hash)
    first.mark_used(NOW + timedelta(minutes=1))
    second.mark_used(NOW + timedelta(minutes=2))
    assert tokens.consume(first) is True
    assert tokens.consume(second) is False  # otro lo consumió antes
    assert tokens.find_by_hash(token.token_hash).used_at == first.used_at


def test_consume_requires_a_used_token(db_session):
    tokens = SqlAlchemyResetTokenRepository(db_session)
    token = PasswordResetToken.create(id=uuid4(), user_id=uuid4(), token_hash="a" * 64, expires_at=NOW, now=NOW)
    with pytest.raises(ValueError):
        tokens.consume(token)
