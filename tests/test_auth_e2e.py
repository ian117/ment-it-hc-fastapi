"""E2E de /auth/* contra PostgreSQL real (TestClient, esquema de Alembic).

El rate limit (5/min por IP, en memoria) se reinicia antes de cada test (conftest).
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import text

PASSWORD = "secret12345"
RESET_REQUESTED = "If the email exists, a reset link was sent"


def _email(prefix: str = "auth") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


def _assert_problem(r, status, slug):
    assert r.status_code == status, r.text
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert {"type", "title", "status", "detail", "instance"} <= set(body)
    assert body["type"] == f"https://errors.local/{slug}"
    assert body["status"] == status
    return body


def _register(client, email=None, password=PASSWORD):
    email = email or _email()
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    return email, r.json()


def _login(client, email, password=PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def _request_reset(client, email):
    return client.post("/auth/password-reset/request", json={"email": email})


# -- register --------------------------------------------------------------------


def test_register_returns_201_with_normalized_email_and_no_hash(client):
    raw = f"  Mixed-{uuid.uuid4().hex[:8]}@Example.COM "
    r = client.post("/auth/register", json={"email": raw.strip(), "password": PASSWORD})
    assert r.status_code == 201, r.text
    body = r.json()
    assert set(body) == {"id", "email", "createdAt"}
    assert body["email"] == raw.strip().lower()
    uuid.UUID(body["id"])
    datetime.fromisoformat(body["createdAt"].replace("Z", "+00:00"))


def test_register_duplicate_email_is_409_even_with_different_case(client):
    email, _ = _register(client)
    r = client.post("/auth/register", json={"email": email.upper(), "password": PASSWORD})
    body = _assert_problem(r, 409, "email-already-registered")
    assert body["title"] == "Email already registered"
    assert body["detail"] == "Email already registered"


@pytest.mark.parametrize(
    "payload,fields",
    [
        ({"email": "not-an-email", "password": "short"}, {"email", "password"}),
        ({"email": _email(), "password": "x" * 129}, {"password"}),
        ({"email": _email()}, {"password"}),
        ({"email": _email(), "password": PASSWORD, "isAdmin": True}, {"isAdmin"}),
    ],
)
def test_register_invalid_body_is_400_with_field_errors(client, payload, fields):
    body = _assert_problem(client.post("/auth/register", json=payload), 400, "validation-error")
    assert {e["field"] for e in body["errors"]} == fields


# -- login -----------------------------------------------------------------------


def test_login_returns_bearer_token_with_integer_expires_in(client):
    email, user = _register(client)
    r = _login(client, email.upper())  # el email se normaliza también al entrar
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"accessToken", "tokenType", "expiresIn"}
    assert body["tokenType"] == "Bearer"
    assert body["expiresIn"] == 3600 and isinstance(body["expiresIn"], int)
    claims = jwt.decode(body["accessToken"], options={"verify_signature": False})
    assert claims["sub"] == user["id"] and claims["type"] == "access"
    assert set(claims) == {"sub", "iat", "exp", "type"}


def test_login_bad_credentials_are_a_single_401(client):
    email, _ = _register(client)
    wrong_password = _assert_problem(_login(client, email, "wrong-password"), 401, "unauthorized")
    unknown_email = _assert_problem(_login(client, _email("ghost")), 401, "unauthorized")
    malformed = _assert_problem(_login(client, "not-an-email-at-all"), 400, "validation-error")
    assert wrong_password["detail"] == unknown_email["detail"] == "Invalid credentials"
    assert malformed["errors"][0]["field"] == "email"


def test_login_empty_password_is_400(client):
    body = _assert_problem(_login(client, _email(), ""), 400, "validation-error")
    assert body["errors"][0]["field"] == "password"


def test_sixth_login_attempt_in_a_minute_is_429(client):
    email, _ = _register(client)
    for _ in range(5):
        _assert_problem(_login(client, email, "wrong-password"), 401, "unauthorized")
    _assert_problem(_login(client, email, "wrong-password"), 429, "too-many-requests")
    _assert_problem(_login(client, email), 429, "too-many-requests")  # ni siquiera la correcta


# -- me --------------------------------------------------------------------------


def test_me_returns_the_authenticated_user(client, make_user):
    user = make_user()
    r = client.get("/auth/me", headers=user.headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"id", "email", "createdAt"}
    assert (body["id"], body["email"]) == (user.id, user.email)


def test_me_with_the_login_token(client):
    email, user = _register(client)
    token = _login(client, email).json()["accessToken"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200 and r.json()["id"] == user["id"]


def test_me_without_token_is_401_with_www_authenticate(client):
    r = client.get("/auth/me")
    _assert_problem(r, 401, "unauthorized")
    assert r.headers["www-authenticate"] == "Bearer"


def test_me_with_tampered_or_foreign_tokens_is_401(client, make_user):
    token = make_user().headers["Authorization"].removeprefix("Bearer ")
    now = datetime.now(timezone.utc)
    claims = {"sub": str(uuid.uuid4()), "iat": now, "exp": now + timedelta(hours=1), "type": "access"}
    bad = [
        token + "x",
        token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB"),
        jwt.encode(claims, "another-secret-that-is-long-enough-32", algorithm="HS256"),
        "garbage",
    ]
    for value in bad:
        _assert_problem(client.get("/auth/me", headers={"Authorization": f"Bearer {value}"}), 401, "unauthorized")


def test_me_with_a_valid_token_of_a_missing_user_is_401(client):
    from fastappi_notification import container

    ghost = container.token_issuer.issue(uuid.uuid4()).access_token
    body = _assert_problem(client.get("/auth/me", headers={"Authorization": f"Bearer {ghost}"}), 401, "unauthorized")
    assert body["detail"] == "Invalid token"


def test_me_with_an_expired_token_is_401(client):
    from fastappi_notification.core.config import get_settings

    now = datetime.now(timezone.utc)
    settings = get_settings()
    expired = jwt.encode(
        {"sub": str(uuid.uuid4()), "iat": now - timedelta(hours=2), "exp": now - timedelta(hours=1), "type": "access"},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    _assert_problem(client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"}), 401, "unauthorized")


# -- password reset ----------------------------------------------------------------


def test_reset_request_returns_token_for_existing_user_and_none_otherwise(client):
    email, _ = _register(client)
    known = _request_reset(client, email)
    assert known.status_code == 202, known.text
    assert known.json()["message"] == RESET_REQUESTED
    assert len(known.json()["resetToken"]) >= 43

    unknown = _request_reset(client, _email("ghost"))
    assert unknown.status_code == 202
    assert unknown.json() == {"message": RESET_REQUESTED}  # mismo message, sin resetToken


def test_reset_request_hides_the_token_in_production(client):
    from fastappi_notification.api import deps
    from fastappi_notification.main import app

    email, _ = _register(client)
    app.dependency_overrides[deps.expose_reset_token] = lambda: False
    try:
        r = _request_reset(client, email)
    finally:
        del app.dependency_overrides[deps.expose_reset_token]
    assert r.status_code == 202 and r.json() == {"message": RESET_REQUESTED}


def test_reset_request_invalid_email_is_400_and_sixth_request_is_429(client):
    body = _assert_problem(_request_reset(client, "nope"), 400, "validation-error")
    assert body["errors"][0]["field"] == "email"
    for _ in range(5):
        assert _request_reset(client, _email("ghost")).status_code == 202
    _assert_problem(_request_reset(client, _email("ghost")), 429, "too-many-requests")


def test_reset_token_is_stored_hashed_only(client, db_session):
    email, user = _register(client)
    token = _request_reset(client, email).json()["resetToken"]
    rows = db_session.execute(
        text("SELECT token_hash, used_at FROM password_reset_tokens WHERE user_id = :u"), {"u": user["id"]}
    ).all()
    assert len(rows) == 1
    assert rows[0].used_at is None
    assert rows[0].token_hash != token and len(rows[0].token_hash) == 64


def test_confirm_changes_the_password_and_the_token_is_single_use(client):
    email, _ = _register(client)
    token = _request_reset(client, email).json()["resetToken"]

    r = client.post("/auth/password-reset/confirm", json={"token": token, "newPassword": "brand-new-pass"})
    assert r.status_code == 200, r.text
    assert r.json() == {"message": "Password updated"}

    assert _login(client, email, "brand-new-pass").status_code == 200
    _assert_problem(_login(client, email, PASSWORD), 401, "unauthorized")

    again = client.post("/auth/password-reset/confirm", json={"token": token, "newPassword": "another-pass-1"})
    body = _assert_problem(again, 400, "invalid-reset-token")
    assert body["detail"] == "Invalid, expired or already used token"
    assert _login(client, email, "brand-new-pass").status_code == 200  # no se cambió otra vez


def test_confirm_with_unknown_token_is_400(client):
    r = client.post("/auth/password-reset/confirm", json={"token": "does-not-exist", "newPassword": "brand-new-pass"})
    _assert_problem(r, 400, "invalid-reset-token")


def test_confirm_with_expired_token_is_400_and_keeps_the_password(client, db_session):
    email, user = _register(client)
    token = _request_reset(client, email).json()["resetToken"]
    db_session.execute(
        text("UPDATE password_reset_tokens SET expires_at = now() - interval '1 minute' WHERE user_id = :u"),
        {"u": user["id"]},
    )
    db_session.commit()

    r = client.post("/auth/password-reset/confirm", json={"token": token, "newPassword": "brand-new-pass"})
    _assert_problem(r, 400, "invalid-reset-token")
    assert _login(client, email).status_code == 200


@pytest.mark.parametrize(
    "payload,fields",
    [
        ({"token": "", "newPassword": "brand-new-pass"}, {"token"}),
        ({"token": "t", "newPassword": "short"}, {"newPassword"}),
        ({"token": "t", "newPassword": "x" * 129}, {"newPassword"}),
        ({"token": "t", "newPassword": "brand-new-pass", "extra": 1}, {"extra"}),
        ({}, {"token", "newPassword"}),
    ],
)
def test_confirm_invalid_body_is_400(client, payload, fields):
    body = _assert_problem(client.post("/auth/password-reset/confirm", json=payload), 400, "validation-error")
    assert {e["field"] for e in body["errors"]} == fields


# -- el token emitido sirve para el resto de la API --------------------------------


def test_full_cycle_register_login_create_notification_on_alembic_schema(client):
    """Registro -> login -> POST /notifications sobre el esquema REAL de Alembic."""
    email, _ = _register(client)
    token = _login(client, email).json()["accessToken"]
    r = client.post(
        "/notifications",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Hola", "content": "Cuerpo", "channel": "email", "payload": {"recipient": "ana@example.com"}},
    )
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "sent"
