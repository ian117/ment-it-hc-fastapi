import pytest

from fastappi_notification.domain.email import Email
from fastappi_notification.domain.errors import EmailAlreadyRegistered, InvalidEmail
from fastappi_notification.domain.user import User
from tests.application.auth_fakes import EMAIL, PASSWORD, AuthWorld


def test_registra_y_devuelve_el_usuario():
    w = AuthWorld()
    user = w.register.execute(email=EMAIL, password=PASSWORD)
    assert user.email == Email.create(EMAIL)
    assert user.created_at == w.clock.now()
    assert user.updated_at == w.clock.now()
    assert w.users.find_by_id(user.id) is not None


def test_normaliza_el_email_a_minusculas():
    w = AuthWorld()
    user = w.register.execute(email="  Ana@Example.COM ", password=PASSWORD)
    assert user.email.value == "ana@example.com"
    assert w.users.find_by_email(Email.create("ana@example.com")) is not None


def test_guarda_el_hash_y_nunca_la_contrasena_en_claro():
    w = AuthWorld()
    user = w.register.execute(email=EMAIL, password=PASSWORD)
    stored = w.users.stored(user.id)
    assert stored.password_hash.value == "hashed:" + PASSWORD
    assert PASSWORD != stored.password_hash.value


def test_email_duplicado_lanza_y_no_hashea():
    w = AuthWorld()
    w.registered_user()
    hashes_before = len(w.hasher.hash_calls)
    with pytest.raises(EmailAlreadyRegistered):
        w.register.execute(email=EMAIL.upper(), password="otra-contrasena")
    assert len(w.hasher.hash_calls) == hashes_before


def test_duplicado_por_carrera_lo_resuelve_save():
    w = AuthWorld()
    # Otro proceso inserta el mismo email después del chequeo previo de `find_by_email`.
    original_find = w.users.find_by_email

    def find_then_insert(email):
        result = original_find(email)
        w.users.insert_directly(
            User.create(
                id=w.ids.new_id(),
                email=email,
                password_hash=w.hasher.hash("x"),
                now=w.clock.now(),
            )
        )
        return result

    w.users.find_by_email = find_then_insert  # type: ignore[method-assign]
    with pytest.raises(EmailAlreadyRegistered):
        w.register.execute(email=EMAIL, password=PASSWORD)


def test_email_invalido_lanza_y_no_guarda():
    w = AuthWorld()
    with pytest.raises(InvalidEmail):
        w.register.execute(email="no-es-email", password=PASSWORD)
    assert w.users.is_empty()
    assert w.hasher.hash_calls == []
