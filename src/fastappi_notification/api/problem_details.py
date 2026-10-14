"""RFC 9457 Problem Details para toda la API (ADR-006, ADR-012).

Los errores de dominio se mapean aquí, no en los routers. Nunca se filtran
trazas ni detalles internos.
"""

from __future__ import annotations

import logging
import re
from http import HTTPStatus
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..domain.errors import (
    ChannelRuleViolation,
    NotificationNotEditable,
    NotificationNotFound,
    UnknownChannel,
)

logger = logging.getLogger("fastappi_notification")

PROBLEM_MEDIA_TYPE = "application/problem+json"
TYPE_BASE = "https://errors.local/"

# Estados con slug/título fijados por el ADR-012; el resto se deriva de la frase HTTP.
_GENERIC: dict[int, tuple[str, str]] = {
    400: ("bad-request", "Bad request"),
    401: ("unauthorized", "Unauthorized"),
    404: ("not-found", "Not found"),
    409: ("conflict", "Conflict"),
    429: ("too-many-requests", "Too many requests"),
}


class AppError(Exception):
    """Error HTTP genérico del auth heredado (hasta F7). Se traduce según su status."""

    def __init__(self, status_code: int, message: str, error_type: str = "error") -> None:
        self.status_code = status_code
        self.message = message
        self.error_type = error_type  # ignorado: el slug sale del status
        super().__init__(message)


def _generic(status: int) -> tuple[str, str]:
    if status in _GENERIC:
        return _GENERIC[status]
    try:
        phrase = HTTPStatus(status).phrase
    except ValueError:
        phrase = "Error"
    return re.sub(r"[^a-z0-9]+", "-", phrase.lower()).strip("-"), phrase


def problem(
    request: Request,
    status: int,
    slug: str,
    title: str,
    detail: Optional[str] = None,
    errors: Optional[list[dict[str, str]]] = None,
    headers: Optional[dict[str, str]] = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"{TYPE_BASE}{slug}",
        "title": title,
        "status": status,
        "detail": detail if detail is not None else title,
        "instance": request.url.path,
    }
    if errors:
        body["errors"] = errors
    return JSONResponse(body, status_code=status, media_type=PROBLEM_MEDIA_TYPE, headers=headers)


def _field_from_loc(loc: tuple[Any, ...], error_type: str) -> str:
    if error_type == "json_invalid":
        return "body"
    parts = [str(p) for p in loc[1:]] if loc and loc[0] in ("body", "query", "path", "header") else [str(p) for p in loc]
    return ".".join(parts) or "body"


def _clean_message(message: str) -> str:
    return message.removeprefix("Value error, ")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotificationNotFound)
    async def _not_found(request: Request, exc: NotificationNotFound):
        return problem(request, 404, "notification-not-found", "Notification not found")

    @app.exception_handler(NotificationNotEditable)
    async def _not_editable(request: Request, exc: NotificationNotEditable):
        return problem(request, 409, "notification-not-editable", "Notification not editable", str(exc))

    @app.exception_handler(UnknownChannel)
    async def _unknown_channel(request: Request, exc: UnknownChannel):
        return problem(
            request,
            400,
            "unknown-channel",
            "Unknown channel",
            str(exc),
            [{"field": "channel", "message": str(exc)}],
        )

    @app.exception_handler(ChannelRuleViolation)
    async def _rule_violation(request: Request, exc: ChannelRuleViolation):
        return problem(
            request,
            400,
            "channel-rule-violation",
            "Channel rule violation",
            "The notification does not satisfy the channel rules",
            exc.violations,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        errors = [
            {
                "field": _field_from_loc(tuple(err["loc"]), err["type"]),
                "message": _clean_message(err["msg"]),
            }
            for err in exc.errors()
        ]
        return problem(
            request, 400, "validation-error", "Validation failed", "Request validation failed", errors
        )

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limit(request: Request, exc: RateLimitExceeded):
        return problem(request, 429, "too-many-requests", "Too many requests", "Rate limit exceeded")

    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        slug, title = _generic(exc.status_code)
        return problem(request, exc.status_code, slug, title, exc.message)

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception(request: Request, exc: StarletteHTTPException):
        slug, title = _generic(exc.status_code)
        headers = getattr(exc, "headers", None)
        return problem(request, exc.status_code, slug, title, str(exc.detail), headers=headers)

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception):
        logger.exception("Unhandled exception")
        return problem(
            request, 500, "internal-error", "Internal server error", "An unexpected error occurred"
        )
