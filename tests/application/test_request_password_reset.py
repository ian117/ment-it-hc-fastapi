from datetime import timedelta

import pytest

from fastappi_notification.domain.errors import InvalidEmail
from tests.application.auth_fakes import EMAIL, AuthWorld


def test_usuario_existente_devuelve_el_token_en_claro():
    w = AuthWorld()
    w.registered_user()
    token = w.request_reset.execute(email=EMAIL)
    assert token == "reset-token-1"


def test_en_el_repo_solo_queda_el_hash():
    w = AuthWorld()
    user = w.registered_user()
    token = w.request_reset.execute(email=EMAIL)
    [stored] = w.reset_tokens.all()
    assert stored.token_hash == w.generator.hash(token)
    assert len(stored.token_hash) == 64
    assert stored.token_hash != token
    assert stored.user_id == user.id
    assert stored.used_at is None


def test_expira_en_now_mas_ttl():
    w = AuthWorld(ttl_minutes=15)
    w.registered_user()
    w.request_reset.execute(email=EMAIL)
    [stored] = w.reset_tokens.all()
    assert stored.created_at == w.clock.now()
    assert stored.expires_at == w.clock.now() + timedelta(minutes=15)


def test_respeta_un_ttl_distinto():
    w = AuthWorld(ttl_minutes=5)
    w.registered_user()
    w.request_reset.execute(email=EMAIL)
    [stored] = w.reset_tokens.all()
    assert stored.expires_at == w.clock.now() + timedelta(minutes=5)


def test_email_se_normaliza():
    w = AuthWorld()
    w.registered_user()
    assert w.request_reset.execute(email="  ANA@Example.com ") is not None


def test_usuario_inexistente_devuelve_none_y_no_guarda_nada():
    w = AuthWorld()
    assert w.request_reset.execute(email="nadie@example.com") is None
    assert w.reset_tokens.is_empty()


def test_email_invalido_lanza_invalid_email():
    w = AuthWorld()
    with pytest.raises(InvalidEmail):
        w.request_reset.execute(email="basura")
    assert w.reset_tokens.is_empty()
