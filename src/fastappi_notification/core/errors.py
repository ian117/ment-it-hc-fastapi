"""Forma única de error para toda la API (criterio 9).

Todo error —de validación, de negocio o inesperado— sale con la misma
estructura:

    {"error": {"type": "...", "message": "...", "details": [...]}}

Los errores de validación conservan qué campo falló en `details`. Ningún
handler filtra SQL, nombres de tablas ni trazas internas.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("fastappi_notification")


class AppError(Exception):
    """Error de negocio con código HTTP y forma controlada."""

    def __init__(self, status_code: int, message: str, error_type: str = "error"):
        self.status_code = status_code
        self.message = message
        self.error_type = error_type
        super().__init__(message)


def _error_body(error_type: str, message: str, details: list | None = None) -> dict:
    body: dict = {"error": {"type": error_type, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.error_type, exc.message),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body("http_error", str(exc.detail)),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(request: Request, exc: RequestValidationError):
        details = [
            {"field": ".".join(str(p) for p in err["loc"]), "message": err["msg"]}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body("validation_error", "Validation failed", details),
        )

    @app.exception_handler(RateLimitExceeded)
    async def _handle_rate_limit(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=_error_body("rate_limited", "Too many requests, slow down"),
        )

    @app.exception_handler(IntegrityError)
    async def _handle_integrity_error(request: Request, exc: IntegrityError):
        # No exponemos el detalle de la base (nombres de tablas, constraints).
        # Lo logueamos para diagnóstico y devolvemos un 409 genérico.
        logger.warning("IntegrityError: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error_body("conflict", "Resource conflict"),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception):
        # Catch-all: nunca dejamos escapar la traza al cliente.
        logger.exception("Unhandled exception")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("internal_error", "Internal server error"),
        )
