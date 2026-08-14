from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Cabeceras de seguridad HTTP (criterio 8). Conjunto conservador y sin estado.
# HSTS solo tiene efecto real detrás de TLS; se incluye porque en producción la
# app va detrás de un proxy con HTTPS.
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response
