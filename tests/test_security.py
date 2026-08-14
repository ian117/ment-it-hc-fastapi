"""Tests unitarios de las utilidades de seguridad. No tocan la base de datos:
son los tests "rápidos" del criterio 15."""

import jwt
import pytest

from fastappi_notification.core.security import (
    create_access_token,
    decode_access_token,
    generate_reset_token,
    hash_password,
    hash_reset_token,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("s3cret-password")
    assert hashed != "s3cret-password"
    assert verify_password("s3cret-password", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip():
    token = create_access_token("42")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["type"] == "access"


def test_tampered_token_is_rejected():
    token = create_access_token("42")
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token + "tampered")


def test_reset_token_stores_only_hash():
    raw, hashed = generate_reset_token()
    # El hash guardado no permite recuperar el token en claro (criterio 4).
    assert raw != hashed
    assert hash_reset_token(raw) == hashed
    assert len(hashed) == 64  # sha256 hex
