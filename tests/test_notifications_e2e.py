"""E2E de /notifications contra PostgreSQL real (TestClient).

Destinatarios deterministas (ADR-012): email/push con 'fail' y sms terminado en
'0000' fallan; el resto se entrega.
"""

import uuid

import pytest

OK_EMAIL = "ana@example.com"
FAIL_EMAIL = "fail@example.com"
OK_SMS = "+5219611234567"
FAIL_SMS = "+5219610000000"
OK_PUSH = "device-token-1"
FAIL_PUSH = "device-fail-1"

NOTIFICATION_KEYS = {
    "id", "title", "content", "channel", "payload", "status", "attempts",
    "errorMessage", "sentAt", "createdAt", "updatedAt",
}


def _create(client, user, *, channel="email", recipient=OK_EMAIL, title="Hola", content="Cuerpo"):
    return client.post(
        "/notifications",
        headers=user.headers,
        json={"title": title, "content": content, "channel": channel, "payload": {"recipient": recipient}},
    )


def _assert_problem(r, status, slug):
    assert r.status_code == status, r.text
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert {"type", "title", "status", "detail", "instance"} <= set(body)
    assert body["type"] == f"https://errors.local/{slug}"
    assert body["status"] == status
    return body


def _total(client, user) -> int:
    return client.get("/notifications", headers=user.headers).json()["total"]


# -- Auth + creación -------------------------------------------------------------


def test_register_login_then_create_with_the_issued_token(client):
    email = f"flow-{uuid.uuid4().hex[:10]}@example.com"
    assert client.post("/auth/register", json={"email": email, "password": "secret12345"}).status_code == 201
    r = client.post("/auth/login", json={"email": email, "password": "secret12345"})
    assert r.status_code == 200
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = client.post(
        "/notifications",
        headers=headers,
        json={"title": "t", "content": "c", "channel": "push", "payload": {"recipient": OK_PUSH}},
    )
    assert r.status_code == 201
    assert r.json()["status"] == "sent"


def test_post_sent_has_contract_shape(client, make_user):
    user = make_user()
    r = _create(client, user)
    assert r.status_code == 201
    body = r.json()
    assert set(body) == NOTIFICATION_KEYS  # sin userId
    uuid.UUID(body["id"])
    assert body["status"] == "sent"
    assert body["attempts"] == 1
    assert body["errorMessage"] is None
    assert body["sentAt"] is not None
    assert body["payload"] == {"recipient": OK_EMAIL}
    assert body["channel"] == "email"
    assert body["createdAt"].endswith("Z") or body["createdAt"].endswith("+00:00")


@pytest.mark.parametrize(
    "channel, recipient",
    [("email", FAIL_EMAIL), ("sms", FAIL_SMS), ("push", FAIL_PUSH)],
)
def test_post_failed_is_still_201(client, make_user, channel, recipient):
    user = make_user()
    r = _create(client, user, channel=channel, recipient=recipient)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "failed"
    assert body["attempts"] == 1
    assert body["errorMessage"] == "Simulated delivery failure"
    assert body["sentAt"] is None


# -- Errores de creación ---------------------------------------------------------


def test_sms_over_160_chars_is_400_and_writes_nothing(client, make_user):
    user = make_user()
    r = _create(client, user, channel="sms", recipient=OK_SMS, content="x" * 161)
    body = _assert_problem(r, 400, "channel-rule-violation")
    assert body["errors"][0]["field"] == "content"
    assert _total(client, user) == 0


def test_invalid_recipient_is_channel_rule_violation(client, make_user):
    user = make_user()
    body = _assert_problem(_create(client, user, channel="email", recipient="nope"), 400, "channel-rule-violation")
    assert body["errors"][0]["field"] == "payload.recipient"
    assert _total(client, user) == 0


def test_unknown_channel(client, make_user):
    user = make_user()
    body = _assert_problem(_create(client, user, channel="fax"), 400, "unknown-channel")
    assert body["errors"][0]["field"] == "channel"
    assert _total(client, user) == 0


def test_validation_errors_are_400_not_422(client, make_user):
    user = make_user()
    r = client.post("/notifications", headers=user.headers, json={"title": "", "content": "c", "channel": "sms", "payload": {}})
    body = _assert_problem(r, 400, "validation-error")
    assert {e["field"] for e in body["errors"]} == {"title", "payload.recipient"}


def test_extra_properties_are_rejected(client, make_user):
    user = make_user()
    r = client.post(
        "/notifications",
        headers=user.headers,
        json={"title": "t", "content": "c", "channel": "email", "payload": {"recipient": OK_EMAIL}, "userId": "x"},
    )
    body = _assert_problem(r, 400, "validation-error")
    assert body["errors"][0]["field"] == "userId"


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer garbage"}])
def test_missing_or_invalid_token_is_401_problem(client, headers):
    for method, path in [("get", "/notifications"), ("post", "/notifications"), ("get", f"/notifications/{uuid.uuid4()}")]:
        r = getattr(client, method)(path, headers=headers)
        _assert_problem(r, 401, "unauthorized")


def test_unknown_route_is_not_found_problem(client):
    body = _assert_problem(client.get("/nope"), 404, "not-found")
    assert body["instance"] == "/nope"


# -- Lectura ---------------------------------------------------------------------


def test_list_is_paginated_newest_first(client, make_user):
    user = make_user()
    created = [_create(client, user, title=f"n{i}").json()["id"] for i in range(3)]

    r = client.get("/notifications", headers=user.headers)
    assert r.status_code == 200
    page = r.json()
    assert set(page) == {"data", "total", "page", "limit"}
    assert (page["total"], page["page"], page["limit"]) == (3, 1, 20)
    assert [n["id"] for n in page["data"]] == list(reversed(created))
    assert set(page["data"][0]) == NOTIFICATION_KEYS

    r = client.get("/notifications?page=2&limit=2", headers=user.headers)
    assert [n["id"] for n in r.json()["data"]] == [created[0]]
    assert r.json()["total"] == 3


@pytest.mark.parametrize("query, field", [("limit=101", "limit"), ("limit=0", "limit"), ("page=0", "page"), ("page=abc", "page")])
def test_list_out_of_range_params_are_400(client, make_user, query, field):
    user = make_user()
    body = _assert_problem(client.get(f"/notifications?{query}", headers=user.headers), 400, "validation-error")
    assert body["errors"][0]["field"] == field


def test_list_only_returns_own_notifications(client, make_user):
    a, b = make_user(), make_user()
    _create(client, a)
    assert _total(client, b) == 0
    assert _total(client, a) == 1


def test_get_own_and_foreign(client, make_user):
    a, b = make_user(), make_user()
    nid = _create(client, a).json()["id"]
    r = client.get(f"/notifications/{nid}", headers=a.headers)
    assert r.status_code == 200 and r.json()["id"] == nid
    _assert_problem(client.get(f"/notifications/{nid}", headers=b.headers), 404, "notification-not-found")
    _assert_problem(client.get(f"/notifications/{uuid.uuid4()}", headers=a.headers), 404, "notification-not-found")


def test_invalid_uuid_in_path_is_404(client, make_user):
    user = make_user()
    for method in ("get", "patch", "delete"):
        kwargs = {"json": {"title": "x"}} if method == "patch" else {}
        r = getattr(client, method)("/notifications/not-a-uuid", headers=user.headers, **kwargs)
        _assert_problem(r, 404, "notification-not-found")


# -- PATCH -----------------------------------------------------------------------


def test_patch_sent_is_409(client, make_user):
    user = make_user()
    nid = _create(client, user).json()["id"]
    r = client.patch(f"/notifications/{nid}", headers=user.headers, json={"title": "nuevo"})
    body = _assert_problem(r, 409, "notification-not-editable")
    assert body["detail"] == "Only failed notifications can be edited"
    assert client.get(f"/notifications/{nid}", headers=user.headers).json()["title"] == "Hola"


def test_patch_failed_with_valid_recipient_resends_and_succeeds(client, make_user):
    user = make_user()
    created = _create(client, user, channel="sms", recipient=FAIL_SMS).json()
    assert created["status"] == "failed"

    r = client.patch(
        f"/notifications/{created['id']}",
        headers=user.headers,
        json={"title": "Corregido", "payload": {"recipient": OK_SMS}},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "sent"
    assert body["attempts"] == 2
    assert body["title"] == "Corregido"
    assert body["payload"] == {"recipient": OK_SMS}
    assert body["errorMessage"] is None
    assert body["sentAt"] is not None
    assert body["channel"] == "sms"
    assert body["updatedAt"] >= created["updatedAt"]


def test_patch_failed_with_another_failing_recipient_stays_failed(client, make_user):
    user = make_user()
    nid = _create(client, user, channel="email", recipient=FAIL_EMAIL).json()["id"]
    r = client.patch(f"/notifications/{nid}", headers=user.headers, json={"payload": {"recipient": "still-fail@example.com"}})
    assert r.status_code == 200
    assert r.json()["status"] == "failed"
    assert r.json()["attempts"] == 2


def test_patch_invalid_payload_is_400_and_notification_stays_failed(client, make_user):
    user = make_user()
    created = _create(client, user, channel="sms", recipient=FAIL_SMS).json()
    r = client.patch(f"/notifications/{created['id']}", headers=user.headers, json={"payload": {"recipient": "12345"}})
    _assert_problem(r, 400, "channel-rule-violation")
    after = client.get(f"/notifications/{created['id']}", headers=user.headers).json()
    assert after["status"] == "failed"
    assert after["attempts"] == 1
    assert after["payload"] == {"recipient": FAIL_SMS}


@pytest.mark.parametrize("body", [{"channel": "email"}, {}, {"title": ""}, {"title": None}])
def test_patch_invalid_bodies_are_400(client, make_user, body):
    user = make_user()
    nid = _create(client, user, recipient=FAIL_EMAIL).json()["id"]
    _assert_problem(client.patch(f"/notifications/{nid}", headers=user.headers, json=body), 400, "validation-error")


def test_patch_foreign_is_404(client, make_user):
    a, b = make_user(), make_user()
    nid = _create(client, a, recipient=FAIL_EMAIL).json()["id"]
    r = client.patch(f"/notifications/{nid}", headers=b.headers, json={"title": "x"})
    _assert_problem(r, 404, "notification-not-found")


# -- DELETE ----------------------------------------------------------------------


def test_delete_then_404(client, make_user):
    user = make_user()
    nid = _create(client, user).json()["id"]
    r = client.delete(f"/notifications/{nid}", headers=user.headers)
    assert r.status_code == 204
    assert r.content == b""
    _assert_problem(client.get(f"/notifications/{nid}", headers=user.headers), 404, "notification-not-found")
    _assert_problem(client.delete(f"/notifications/{nid}", headers=user.headers), 404, "notification-not-found")


def test_delete_foreign_is_404_and_keeps_it(client, make_user):
    a, b = make_user(), make_user()
    nid = _create(client, a).json()["id"]
    _assert_problem(client.delete(f"/notifications/{nid}", headers=b.headers), 404, "notification-not-found")
    assert client.get(f"/notifications/{nid}", headers=a.headers).status_code == 200
