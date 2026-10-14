"""OpenAPI publicado alineado con `contract/openapi.yaml`.

- `problem_responses(...)` documenta por ruta los errores del contrato, con
  `application/problem+json` y el schema `Problem` (RFC 9457, ADR-006).
- `install_openapi(app)` quita lo que FastAPI inventa y esta API no devuelve
  (el 422 y sus schemas: la validación responde 400) y publica `Problem`.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from .problem_details import PROBLEM_MEDIA_TYPE

_DESCRIPTIONS: dict[int, str] = {
    400: "Request inválido o regla del canal violada",
    401: "Token ausente o inválido, o credenciales incorrectas",
    404: "No existe o no pertenece al usuario autenticado",
    409: "Email ya registrado, o notificación no editable",
    429: "Límite de intentos superado",
}

PROBLEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "RFC 9457 Problem Details",
    "required": ["type", "title", "status"],
    "properties": {
        "type": {"type": "string", "format": "uri-reference"},
        "title": {"type": "string"},
        "status": {"type": "integer"},
        "detail": {"type": "string"},
        "instance": {"type": "string"},
        "errors": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["field", "message"],
                "properties": {"field": {"type": "string"}, "message": {"type": "string"}},
            },
        },
    },
}

_VALIDATION_SCHEMAS = ("HTTPValidationError", "ValidationError")


def problem_responses(*codes: int) -> dict[int | str, dict[str, Any]]:
    """Valor para `responses=` de una ruta o router: un Problem por código."""
    return {
        code: {
            "description": _DESCRIPTIONS[code],
            "content": {PROBLEM_MEDIA_TYPE: {"schema": {"$ref": "#/components/schemas/Problem"}}},
        }
        for code in codes
    }


def install_openapi(app: FastAPI) -> None:
    generate = app.openapi  # generador original de FastAPI (cachea en app.openapi_schema)

    def openapi() -> dict[str, Any]:
        schema = generate()
        for path_item in schema.get("paths", {}).values():
            for operation in path_item.values():
                operation.get("responses", {}).pop("422", None)
        schemas = schema.setdefault("components", {}).setdefault("schemas", {})
        for name in _VALIDATION_SCHEMAS:
            schemas.pop(name, None)
        schemas["Problem"] = PROBLEM_SCHEMA
        return schema

    app.openapi = openapi  # type: ignore[method-assign]
