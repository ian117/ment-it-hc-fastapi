import pytest

from fastappi_notification.application.ports import IssuedToken
from fastappi_notification.domain.errors import InvalidCredentials
from tests.application.auth_fakes import EMAIL, PASSWORD, AuthWorld


def test_credenciales_correctas_devuelven_el_token():
    w = AuthWorld()
    user = w.registered_user()
    token = w.login.execute(email=EMAIL, password=PASSWORD)
    assert token == IssuedToken(access_token=f"token-for-{user.id}", expires_in=3600)


def test_el_email_se_normaliza_al_entrar():
    w = AuthWorld()
    w.registered_user()
    assert w.login.execute(email=" ANA@example.com ", password=PASSWORD).expires_in == 3600


def test_contrasena_incorrecta():
    w = AuthWorld()
    w.registered_user()
    with pytest.raises(InvalidCredentials):
        w.login.execute(email=EMAIL, password="mala")


def test_email_inexistente_es_invalid_credentials():
    with pytest.raises(InvalidCredentials):
        AuthWorld().login.execute(email="nadie@example.com", password=PASSWORD)


def test_email_mal_formado_es_invalid_credentials():
    with pytest.raises(InvalidCredentials):
        AuthWorld().login.execute(email="basura", password=PASSWORD)


def test_email_inexistente_igual_verifica_contra_el_senuelo():
    w = AuthWorld()
    with pytest.raises(InvalidCredentials):
        w.login.execute(email="nadie@example.com", password=PASSWORD)
    assert w.hasher.verify_calls == 1


def test_senuelo_se_genera_una_sola_vez():
    w = AuthWorld()
    for _ in range(3):
        with pytest.raises(InvalidCredentials):
            w.login.execute(email="nadie@example.com", password=PASSWORD)
    assert w.hasher.verify_calls == 3
    assert len(w.hasher.hash_calls) == 1


def test_con_usuario_existente_verifica_una_sola_vez():
    w = AuthWorld()
    w.registered_user()
    w.hasher.verify_calls = 0
    w.login.execute(email=EMAIL, password=PASSWORD)
    assert w.hasher.verify_calls == 1


def test_login_with_a_provided_decoy_never_hashes_one_per_instance():
    """La composición crea un `Login` por request: el señuelo llega ya hecho y no se
    hashea otro, así el tiempo no delata si el email existe (ADR-013)."""
    from fastappi_notification.application.use_cases.login import Login
    from fastappi_notification.domain.errors import InvalidCredentials
    from fastappi_notification.domain.password_hash import PasswordHash

    w = AuthWorld()
    for _ in range(2):  # dos instancias, como dos requests
        login = Login(w.users, w.hasher, w.issuer, decoy=PasswordHash("hashed:decoy"))
        with pytest.raises(InvalidCredentials):
            login.execute(email="ghost@example.com", password="whatever1")
    assert w.hasher.hash_calls == []
    assert w.hasher.verify_calls == 2
