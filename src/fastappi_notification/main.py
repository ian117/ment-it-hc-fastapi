import logging

from fastapi import FastAPI

from .api.openapi import install_openapi
from .api.routers import auth, notifications
from .api.problem_details import register_exception_handlers
from .core.limiter import limiter
from .core.middleware import SecurityHeadersMiddleware


def _configure_logging() -> None:
    # Un handler propio en el logger de la app, a nivel INFO, para que los
    # diagnósticos (envíos fallidos, tokens simulados) queden registrados sin
    # depender de la config de logging de uvicorn.
    logger = logging.getLogger("fastappi_notification")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False


def create_app() -> FastAPI:
    _configure_logging()
    app = FastAPI(title="Notifications API", version="0.1.0")

    # slowapi resuelve el limiter desde app.state (criterio 7).
    app.state.limiter = limiter

    app.add_middleware(SecurityHeadersMiddleware)
    register_exception_handlers(app)

    app.include_router(auth.router)
    app.include_router(notifications.router)

    @app.get("/health", tags=["ops"])
    def health() -> dict:
        return {"status": "ok"}

    install_openapi(app)
    return app


app = create_app()
