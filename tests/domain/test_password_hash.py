import pytest

from fastappi_notification.domain.password_hash import PasswordHash


def test_expone_value():
    assert PasswordHash("$argon2id$abc").value == "$argon2id$abc"


def test_igualdad_por_valor():
    assert PasswordHash("x") == PasswordHash("x")


def test_vacio_es_error_de_programacion():
    with pytest.raises(ValueError):
        PasswordHash("")


def test_repr_no_filtra_el_hash():
    assert "argon2" not in repr(PasswordHash("$argon2id$secreto"))
