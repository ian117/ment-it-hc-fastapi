"""Auth heredado (hasta F7): registro, login y errores con el nuevo formato Problem Details."""

import uuid

from fastappi_notification.core.security import decode_access_token


def test_register_login_and_token_subject_is_a_uuid(client):
    email = f"auth-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": "secret12345"})
    assert r.status_code == 201
    body = r.json()
    assert "hashed_password" not in body
    user_id = uuid.UUID(body["id"])

    r = client.post("/auth/login", json={"email": email, "password": "secret12345"})
    assert r.status_code == 200
    assert uuid.UUID(decode_access_token(r.json()["access_token"])["sub"]) == user_id


def test_duplicate_email_is_a_problem_details_409(client):
    email = f"dup-{uuid.uuid4().hex[:10]}@example.com"
    payload = {"email": email, "password": "secret12345"}
    assert client.post("/auth/register", json=payload).status_code == 201
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 409
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["type"] == "https://errors.local/conflict"


def test_invalid_register_body_is_400_not_422(client):
    r = client.post("/auth/register", json={"email": "not-an-email", "password": "short"})
    assert r.status_code == 400
    assert {e["field"] for e in r.json()["errors"]} == {"email", "password"}
