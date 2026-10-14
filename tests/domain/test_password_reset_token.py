from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from fastappi_notification.domain.errors import InvalidResetToken
from fastappi_notification.domain.password_reset_token import PasswordResetToken

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
EXPIRES = T0 + timedelta(minutes=15)
HASH = "a" * 64


def crear() -> PasswordResetToken:
    return PasswordResetToken.create(
        id=uuid4(), user_id=uuid4(), token_hash=HASH, expires_at=EXPIRES, now=T0
    )


def test_create_deja_el_token_sin_usar():
    token = crear()
    assert token.used_at is None
    assert token.created_at == T0
    assert token.expires_at == EXPIRES
    assert token.token_hash == HASH


def test_is_usable_antes_del_vencimiento():
    assert crear().is_usable(EXPIRES - timedelta(microseconds=1)) is True


def test_is_usable_en_el_borde_exacto_ya_no_lo_es():
    assert crear().is_usable(EXPIRES) is False


def test_is_usable_despues_del_vencimiento():
    assert crear().is_usable(EXPIRES + timedelta(seconds=1)) is False


def test_mark_used_fija_used_at():
    token = crear()
    at = T0 + timedelta(minutes=1)
    token.mark_used(at)
    assert token.used_at == at
    assert token.is_usable(at) is False


def test_mark_used_dos_veces_lanza_y_no_muta():
    token = crear()
    first = T0 + timedelta(minutes=1)
    token.mark_used(first)
    with pytest.raises(InvalidResetToken):
        token.mark_used(T0 + timedelta(minutes=2))
    assert token.used_at == first


def test_mark_used_vencido_lanza_y_no_muta():
    token = crear()
    with pytest.raises(InvalidResetToken):
        token.mark_used(EXPIRES)
    assert token.used_at is None


def test_restore_conserva_used_at():
    used = T0 + timedelta(minutes=1)
    token = PasswordResetToken.restore(
        id=uuid4(), user_id=uuid4(), token_hash=HASH, expires_at=EXPIRES, used_at=used, created_at=T0
    )
    assert token.used_at == used
    assert token.is_usable(T0) is False


def test_dominio_no_importa_infraestructura():
    import fastappi_notification.domain as domain_pkg
    from pathlib import Path

    banned = ("fastapi", "sqlalchemy", "pydantic", "hashlib", "secrets")
    for path in Path(domain_pkg.__file__).parent.rglob("*.py"):
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                module = stripped.split()[1].split(".")[0]
                assert module not in banned, f"{path} importa {module}"
