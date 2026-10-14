"""Handlers de Problem Details sobre una app mínima (sin base de datos)."""

import uuid

import pytest
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict
from slowapi import Limiter
from slowapi.util import get_remote_address

from fastappi_notification.api.problem_details import AppError, register_exception_handlers
from fastappi_notification.domain.errors import (
    ChannelRuleViolation,
    NotificationNotEditable,
    NotificationNotFound,
    UnknownChannel,
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

    @app.get("/app-error")
    def app_error():
        raise AppError(409, "Email already registered", "conflict")

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


def test_app_error_maps_by_status(client):
    body = _assert_problem(client.get("/app-error"), 409, "conflict", "Conflict")
    assert body["detail"] == "Email already registered"


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
