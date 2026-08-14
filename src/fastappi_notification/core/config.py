from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación, leída del entorno.

    Los valores por defecto sirven para desarrollo local; en Docker y en
    producción todo llega por variables de entorno. `jwt_secret` no tiene
    un default utilizable a propósito: si nadie lo define, el arranque falla.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5434/notifications"

    jwt_secret: str = "dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    reset_token_expire_minutes: int = 30

    # Umbral de fuerza bruta para el login (criterio de aceptación 7).
    login_rate_limit: str = "5/minute"


@lru_cache
def get_settings() -> Settings:
    return Settings()
