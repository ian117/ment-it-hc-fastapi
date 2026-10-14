from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-only-insecure-secret-change-me"
MIN_PRODUCTION_JWT_SECRET_LENGTH = 32
# Valores conocidos que nunca son válidos en producción (ADR-015).
_KNOWN_INSECURE_SECRETS = {DEV_JWT_SECRET, "randomword"}


class Settings(BaseSettings):
    """Configuración de la aplicación, leída del entorno.

    Los valores por defecto sirven para desarrollo local; en Docker y en
    producción todo llega por variables de entorno (o un `.env`). El default de
    El default de `jwt_secret` es público y solo vale fuera de producción: con
    `environment="production"` la app no arranca si el secreto es un valor conocido o
    tiene menos de 32 caracteres (ADR-015).
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5434/notifications"

    jwt_secret: str = DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    reset_token_expire_minutes: int = 15

    # "production" desactiva `resetToken` en la respuesta de /auth/password-reset/request.
    environment: str = "development"

    # Umbrales de fuerza bruta por IP (formato de slowapi), uno por endpoint (ADR-014).
    login_rate_limit: str = "5/minute"
    reset_request_rate_limit: str = "5/minute"

    @model_validator(mode="after")
    def _require_a_real_secret_in_production(self) -> "Settings":
        if self.environment != "production":
            return self
        if self.jwt_secret in _KNOWN_INSECURE_SECRETS:
            raise ValueError(
                "JWT_SECRET es un valor de desarrollo conocido; define uno propio en producción (ADR-015)."
            )
        if len(self.jwt_secret) < MIN_PRODUCTION_JWT_SECRET_LENGTH:
            raise ValueError(
                f"JWT_SECRET debe tener al menos {MIN_PRODUCTION_JWT_SECRET_LENGTH} caracteres "
                "en producción (ADR-015)."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
