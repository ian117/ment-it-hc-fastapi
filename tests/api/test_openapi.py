"""El /openapi.json publicado cumple lo esencial de contract/openapi.yaml (sin base de datos)."""

import pytest

from fastappi_notification.main import app

EXPECTED = {
    ("/auth/register", "post"): ("201", {"400", "409"}),
    ("/auth/login", "post"): ("200", {"400", "401", "429"}),
    ("/auth/me", "get"): ("200", {"401"}),
    ("/auth/password-reset/request", "post"): ("202", {"400", "429"}),
    ("/auth/password-reset/confirm", "post"): ("200", {"400"}),
    ("/notifications", "post"): ("201", {"400", "401"}),
    ("/notifications", "get"): ("200", {"400", "401"}),
    ("/notifications/{id}", "get"): ("200", {"401", "404"}),
    ("/notifications/{id}", "patch"): ("200", {"400", "401", "404", "409"}),
    ("/notifications/{id}", "delete"): ("204", {"401", "404"}),
}


@pytest.fixture(scope="module")
def spec():
    return app.openapi()


def test_no_422_nor_validation_schemas_anywhere(spec):
    for path, item in spec["paths"].items():
        for method, op in item.items():
            assert "422" not in op["responses"], f"{method} {path}"
    assert "HTTPValidationError" not in spec["components"]["schemas"]
    assert "ValidationError" not in spec["components"]["schemas"]


def test_problem_schema_matches_contract(spec):
    problem = spec["components"]["schemas"]["Problem"]
    assert problem["required"] == ["type", "title", "status"]
    assert set(problem["properties"]) == {"type", "title", "status", "detail", "instance", "errors"}
    assert problem["properties"]["errors"]["items"]["required"] == ["field", "message"]


@pytest.mark.parametrize("route", EXPECTED)
def test_routes_document_contract_status_codes(spec, route):
    path, method = route
    success, errors = EXPECTED[route]
    responses = spec["paths"][path][method]["responses"]
    assert set(responses) == {success} | errors
    for code in errors:
        content = responses[code]["content"]
        assert set(content) == {"application/problem+json"}
        assert content["application/problem+json"]["schema"] == {"$ref": "#/components/schemas/Problem"}
    if success == "204":
        assert "content" not in responses[success]


def test_page_bounds(spec):
    props = spec["components"]["schemas"]["NotificationPage"]["properties"]
    assert (props["total"]["minimum"], props["page"]["minimum"]) == (0, 1)
    assert (props["limit"]["minimum"], props["limit"]["maximum"]) == (1, 100)


def test_revise_request_requires_at_least_one_property(spec):
    revise = spec["components"]["schemas"]["ReviseNotificationRequest"]
    assert revise["minProperties"] == 1
    assert revise["additionalProperties"] is False


def test_channel_is_open_string_and_status_is_closed_enum(spec):
    schemas = spec["components"]["schemas"]
    for model in ("CreateNotificationRequest", "NotificationResponse"):
        channel = schemas[model]["properties"]["channel"]
        assert channel["type"] == "string" and "enum" not in channel
        assert all(name in channel["description"] for name in ("email", "sms", "push"))
    status = schemas["NotificationResponse"]["properties"]["status"]
    # status es un enum cerrado en el contrato (NotificationStatus); channel no (ADR-004).
    assert status["type"] == "string" and status["enum"] == ["pending", "sent", "failed"]


def _props(spec, name):
    return spec["components"]["schemas"][name]["properties"]


def test_auth_requests_are_strict_camel_case_with_contract_bounds(spec):
    schemas = spec["components"]["schemas"]
    for name in ("RegisterRequest", "LoginRequest", "PasswordResetRequest", "PasswordResetConfirm"):
        assert schemas[name]["additionalProperties"] is False, name
    assert (_props(spec, "RegisterRequest")["password"]["minLength"], _props(spec, "RegisterRequest")["password"]["maxLength"]) == (8, 128)
    assert _props(spec, "RegisterRequest")["email"]["maxLength"] == 320
    assert _props(spec, "LoginRequest")["password"]["minLength"] == 1
    confirm = schemas["PasswordResetConfirm"]
    assert set(confirm["properties"]) == {"token", "newPassword"}
    assert confirm["properties"]["token"]["minLength"] == 1
    assert (confirm["properties"]["newPassword"]["minLength"], confirm["properties"]["newPassword"]["maxLength"]) == (8, 128)


def test_auth_responses_are_camel_case(spec):
    assert set(_props(spec, "UserResponse")) == {"id", "email", "createdAt"}
    token = spec["components"]["schemas"]["AccessTokenResponse"]
    assert set(token["properties"]) == {"accessToken", "tokenType", "expiresIn"}
    assert set(token["required"]) == {"accessToken", "tokenType", "expiresIn"}
    assert token["properties"]["tokenType"]["const"] == "Bearer"
    assert set(_props(spec, "PasswordResetRequestedResponse")) == {"message", "resetToken"}
    assert spec["components"]["schemas"]["PasswordResetRequestedResponse"]["required"] == ["message"]
    assert _props(spec, "PasswordResetRequestedResponse")["resetToken"]["type"] == "string"
