"""Handlers de Problem Details sobre una app mínima (sin base de datos)."""

import uuid

import pytest
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict
from slowapi import Limiter
from slowapi.util import get_remote_address

from fastappi_notification.api.problem_details import register_exception_handlers
from fastappi_notification.domain.errors import (
    ChannelRuleViolation,
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidEmail,
    InvalidResetToken,
    NotificationNotEditable,
    NotificationNotFound,
    UnknownChannel,
    UserNotFound,
)


class Inner(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipient: str


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    payload: Inner


def _app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter

    @app.get("/not-found")
    def not_found():
        raise NotificationNotFound(uuid.uuid4())

    @app.get("/not-editable")
    def not_editable():
        raise NotificationNotEditable()

    @app.get("/unknown-channel")
    def unknown_channel():
        raise UnknownChannel("fax")

    @app.get("/rule")
    def rule():
        raise ChannelRuleViolation([{"field": "payload.recipient", "message": "bad"}])

    @app.get("/email-taken")
    def email_taken():
        raise EmailAlreadyRegistered()

    @app.get("/invalid-credentials")
    def invalid_credentials():
        raise InvalidCredentials()

    @app.get("/user-not-found")
    def user_not_found():
        raise UserNotFound(uuid.uuid4())

    @app.get("/invalid-reset-token")
    def invalid_reset_token():
        raise InvalidResetToken()

    @app.get("/invalid-email")
    def invalid_email():
        raise InvalidEmail()

    @app.get("/http-401")
    def http_401():
        raise HTTPException(401, "nope")

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret internals")

    @app.get("/q")
    def q(limit: int = Query(20, ge=1, le=100)):
        return {}

    @app.post("/b")
    def b(body: Body):
        return {}

    @app.get("/limited")
    @limiter.limit("1/minute")
    def limited(request: Request):
        return {}

    return app


@pytest.fixture(scope="module")
def client():
    return TestClient(_app(), raise_server_exceptions=False)


def _assert_problem(r, status, slug, title):
    assert r.status_code == status
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert body["type"] == f"https://errors.local/{slug}"
    assert body["title"] == title
    assert body["status"] == status
    assert isinstance(body["detail"], str)
    assert body["instance"] == r.request.url.path
    return body


def test_notification_not_found(client):
    _assert_problem(client.get("/not-found"), 404, "notification-not-found", "Notification not found")


def test_notification_not_editable(client):
    body = _assert_problem(client.get("/not-editable"), 409, "notification-not-editable", "Notification not editable")
    assert body["detail"] == "Only failed notifications can be edited"


def test_unknown_channel(client):
    body = _assert_problem(client.get("/unknown-channel"), 400, "unknown-channel", "Unknown channel")
    assert body["errors"][0]["field"] == "channel"


def test_channel_rule_violation_exposes_violations(client):
    body = _assert_problem(client.get("/rule"), 400, "channel-rule-violation", "Channel rule violation")
    assert body["errors"] == [{"field": "payload.recipient", "message": "bad"}]
    # El detail lleva el mensaje concreto del dominio, igual que NestJS (F9).
    assert body["detail"] == "payload.recipient: bad"


def test_email_already_registered(client):
    body = _assert_problem(
        client.get("/email-taken"), 409, "email-already-registered", "Email already registered"
    )
    assert body["detail"] == "Email already registered"


def test_invalid_credentials(client):
    body = _assert_problem(client.get("/invalid-credentials"), 401, "unauthorized", "Unauthorized")
    assert body["detail"] == "Invalid credentials"


def test_user_not_found_is_a_generic_401_that_does_not_leak_the_id(client):
    r = client.get("/user-not-found")
    body = _assert_problem(r, 401, "unauthorized", "Unauthorized")
    assert body["detail"] == "Invalid token"
    assert "errors" not in body


def test_invalid_reset_token(client):
    body = _assert_problem(
        client.get("/invalid-reset-token"), 400, "invalid-reset-token", "Invalid reset token"
    )
    assert body["detail"] == "Invalid, expired or already used token"


def test_invalid_email_is_a_validation_error_on_email(client):
    body = _assert_problem(client.get("/invalid-email"), 400, "validation-error", "Validation failed")
    assert body["errors"] == [{"field": "email", "message": "Invalid email address"}]


def test_http_exception_401_and_unknown_route(client):
    _assert_problem(client.get("/http-401"), 401, "unauthorized", "Unauthorized")
    _assert_problem(client.get("/does-not-exist"), 404, "not-found", "Not found")


def test_unhandled_error_is_generic_500(client):
    r = client.get("/boom")
    body = _assert_problem(r, 500, "internal-error", "Internal server error")
    assert "secret" not in r.text
    assert "errors" not in body


def test_query_validation_error_is_400_without_prefix(client):
    body = _assert_problem(client.get("/q?limit=101"), 400, "validation-error", "Validation failed")
    assert body["errors"][0]["field"] == "limit"


def test_body_validation_uses_dotted_paths_and_forbids_extras(client):
    r = client.post("/b", json={"title": "t", "payload": {}, "extra": 1})
    body = _assert_problem(r, 400, "validation-error", "Validation failed")
    fields = {e["field"] for e in body["errors"]}
    assert fields == {"payload.recipient", "extra"}


def test_invalid_json_is_400(client):
    r = client.post("/b", content=b"{not json", headers={"content-type": "application/json"})
    body = _assert_problem(r, 400, "validation-error", "Validation failed")
    assert body["errors"][0]["field"] == "body"


def test_rate_limit_is_429_problem(client):
    assert client.get("/limited").status_code == 200
    _assert_problem(client.get("/limited"), 429, "too-many-requests", "Too many requests")

