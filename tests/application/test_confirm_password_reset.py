from datetime import timedelta

import pytest

from fastappi_notification.domain.errors import InvalidResetToken
from tests.application.auth_fakes import EMAIL, NEW_PASSWORD, PASSWORD, AuthWorld


def preparar(w: AuthWorld | None = None) -> tuple[AuthWorld, object, str]:
    w = w or AuthWorld()
    user = w.registered_user()
    token = w.request_reset.execute(email=EMAIL)
    assert token is not None
    return w, user, token


def hash_actual(w: AuthWorld, user) -> str:
    return w.users.stored(user.id).password_hash.value


def test_cambia_la_contrasena_y_marca_used_at():
    w, user, token = preparar()
    w.clock.advance(minutes=1)
    w.confirm_reset.execute(token=token, new_password=NEW_PASSWORD)
    stored_user = w.users.stored(user.id)
    assert stored_user.password_hash.value == "hashed:" + NEW_PASSWORD
    assert stored_user.updated_at == w.clock.now()
    [stored_token] = w.reset_tokens.all()
    assert stored_token.used_at == w.clock.now()


def test_tras_confirmar_se_puede_entrar_con_la_nueva():
    w, _, token = preparar()
    w.confirm_reset.execute(token=token, new_password=NEW_PASSWORD)
    assert w.login.execute(email=EMAIL, password=NEW_PASSWORD).expires_in == 3600
    from fastappi_notification.domain.errors import InvalidCredentials

    with pytest.raises(InvalidCredentials):
        w.login.execute(email=EMAIL, password=PASSWORD)


def test_segunda_confirmacion_lanza_y_no_cambia_la_contrasena():
    w, user, token = preparar()
    w.confirm_reset.execute(token=token, new_password=NEW_PASSWORD)
    with pytest.raises(InvalidResetToken):
        w.confirm_reset.execute(token=token, new_password="tercera-contrasena")
    assert hash_actual(w, user) == "hashed:" + NEW_PASSWORD


def test_vencido_lanza_y_no_cambia_la_contrasena():
    w, user, token = preparar()
    w.clock.advance(minutes=15)  # borde exacto: ya venció
    with pytest.raises(InvalidResetToken):
        w.confirm_reset.execute(token=token, new_password=NEW_PASSWORD)
    assert hash_actual(w, user) == "hashed:" + PASSWORD
    assert w.reset_tokens.all()[0].used_at is None


def test_justo_antes_del_vencimiento_aun_sirve():
    w, user, token = preparar()
    w.clock.advance(minutes=14, seconds=59)
    w.confirm_reset.execute(token=token, new_password=NEW_PASSWORD)
    assert hash_actual(w, user) == "hashed:" + NEW_PASSWORD


def test_token_inexistente_lanza_y_no_cambia_la_contrasena():
    w, user, _ = preparar()
    with pytest.raises(InvalidResetToken):
        w.confirm_reset.execute(token="no-existe", new_password=NEW_PASSWORD)
    assert hash_actual(w, user) == "hashed:" + PASSWORD


def test_carrera_donde_consume_devuelve_false_no_cambia_la_contrasena():
    w, user, token = preparar()
    [stored] = w.reset_tokens.all()

    def otro_proceso_lo_consume() -> None:
        stored.mark_used(w.clock.now())  # el almacenado ya aparece usado

    w.reset_tokens.before_consume = otro_proceso_lo_consume
    with pytest.raises(InvalidResetToken):
        w.confirm_reset.execute(token=token, new_password=NEW_PASSWORD)
    assert hash_actual(w, user) == "hashed:" + PASSWORD
    assert w.users.stored(user.id).updated_at == user.updated_at


def test_dos_confirmaciones_solo_una_gana():
    w, user, token = preparar()
    results = []
    for password in ("primera-contrasena", "segunda-contrasena"):
        try:
            w.confirm_reset.execute(token=token, new_password=password)
            results.append("ok")
        except InvalidResetToken:
            results.append("invalid")
    assert results == ["ok", "invalid"]
    assert hash_actual(w, user) == "hashed:primera-contrasena"
