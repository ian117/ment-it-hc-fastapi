"""Adaptadores de seguridad (hasher, JWT, generador de token de reseteo). Sin base de datos."""

import hashlib
import re
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt
import pytest

from fastappi_notification.domain.password_hash import PasswordHash
from fastappi_notification.infrastructure.security import (
    Argon2PasswordHasher,
    JwtTokenIssuer,
    JwtTokenVerifier,
    SecretsResetTokenGenerator,
)

SECRET = "unit-test-secret-with-enough-length-32b"
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


class FixedClock:
    def __init__(self, now: datetime = NOW) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current


# -- Argon2PasswordHasher ---------------------------------------------------------


def test_hash_is_not_the_plain_password_and_verifies():
    hasher = Argon2PasswordHasher()
    hashed = hasher.hash("s3cret-password")
    assert isinstance(hashed, PasswordHash)
    assert hashed.value != "s3cret-password"
    assert hashed.value.startswith("$argon2")
    assert hasher.verify("s3cret-password", hashed)
    assert not hasher.verify("wrong", hashed)


def test_same_password_produces_different_hashes():
    hasher = Argon2PasswordHasher()
    assert hasher.hash("same-password").value != hasher.hash("same-password").value


def test_long_and_unicode_passwords_are_hashed_in_full():
    hasher = Argon2PasswordHasher()
    base = "ñ" * 100  # 200 bytes UTF-8, hasta el límite de 128 caracteres del contrato
    hashed = hasher.hash(base + "A")
    assert hasher.verify(base + "A", hashed)
    assert not hasher.verify(base + "B", hashed)


# -- JwtTokenIssuer / JwtTokenVerifier --------------------------------------------


def _issuer(clock=None, seconds=3600) -> JwtTokenIssuer:
    return JwtTokenIssuer(SECRET, "HS256", seconds, clock or FixedClock())


def test_issued_token_has_the_agreed_claims_and_expires_in():
    user_id = uuid4()
    issued = _issuer().issue(user_id)
    assert issued.expires_in == 3600
    claims = jwt.decode(issued.access_token, SECRET, algorithms=["HS256"], options={"verify_exp": False, "verify_iat": False})
    assert set(claims) == {"sub", "iat", "exp", "type"}
    assert claims["sub"] == str(user_id)
    assert claims["type"] == "access"
    assert claims["iat"] == int(NOW.timestamp())
    assert claims["exp"] == int(NOW.timestamp()) + 3600


def test_verifier_returns_the_user_id_of_a_fresh_token():
    user_id = uuid4()
    token = JwtTokenIssuer(SECRET, "HS256", 3600, _SystemNow()).issue(user_id).access_token
    assert JwtTokenVerifier(SECRET, "HS256").verify(token) == user_id


class _SystemNow:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


def _encode(claims: dict, secret: str = SECRET, algorithm: str = "HS256") -> str:
    return jwt.encode(claims, secret, algorithm=algorithm)


def _claims(**overrides) -> dict:
    now = datetime.now(timezone.utc)
    claims = {"sub": str(uuid4()), "iat": now, "exp": now + timedelta(hours=1), "type": "access"}
    claims.update(overrides)
    return {k: v for k, v in claims.items() if v is not None}


@pytest.mark.parametrize(
    "token",
    [
        "",
        "garbage",
        _encode(_claims(), secret="another-secret-also-long-enough-32b"),  # firma ajena
        _encode(_claims(exp=datetime.now(timezone.utc) - timedelta(seconds=5))),  # vencido
        _encode(_claims(type="refresh")),
        _encode(_claims(type=None)),
        _encode(_claims(sub="not-a-uuid")),
        _encode(_claims(sub=None)),
        _encode(_claims(exp=None)),
        _encode(_claims(iat=None)),
    ],
    ids=["empty", "garbage", "bad-signature", "expired", "wrong-type", "no-type", "sub-not-uuid", "no-sub", "no-exp", "no-iat"],
)
def test_verifier_rejects_invalid_tokens(token):
    assert JwtTokenVerifier(SECRET, "HS256").verify(token) is None


def test_verifier_rejects_a_tampered_token():
    token = _issuer(_SystemNow()).issue(uuid4()).access_token
    assert JwtTokenVerifier(SECRET, "HS256").verify(token + "tampered") is None


def test_verifier_rejects_the_none_algorithm():
    token = jwt.encode(_claims(), None, algorithm="none")
    assert JwtTokenVerifier(SECRET, "HS256").verify(token) is None


# -- SecretsResetTokenGenerator ---------------------------------------------------


def test_generate_returns_token_and_its_sha256_hex():
    generator = SecretsResetTokenGenerator()
    generated = generator.generate()
    assert generated.token_hash == hashlib.sha256(generated.token.encode()).hexdigest()
    assert re.fullmatch(r"[0-9a-f]{64}", generated.token_hash)
    assert generated.token != generated.token_hash
    assert generator.hash(generated.token) == generated.token_hash


def test_tokens_are_unique_and_high_entropy():
    generator = SecretsResetTokenGenerator()
    tokens = {generator.generate().token for _ in range(50)}
    assert len(tokens) == 50
    assert all(len(t) >= 43 for t in tokens)  # token_urlsafe(32) -> 43 caracteres


def test_hash_is_deterministic():
    assert SecretsResetTokenGenerator().hash("abc") == hashlib.sha256(b"abc").hexdigest()
