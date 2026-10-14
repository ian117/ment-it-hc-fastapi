"""Utilidades para construir bases de test con el esquema REAL de Alembic.

`create_all` no sirve para tests de esquema: oculta diferencias entre los
modelos y las migraciones (p. ej. un DEFAULT de columna quitado por una migración).
"""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

# Base de tests separada de la de desarrollo para no pisar datos.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5434/notifications_test",
)
# Los tests de migración usan su propia base para no tocar el esquema que usa el e2e.
MIGRATION_DATABASE_URL = TEST_DATABASE_URL + "_migrations"

_ROOT = Path(__file__).resolve().parent.parent


def _split(url: str) -> tuple[str, str]:
    base, _, name = url.rpartition("/")
    return base, name


def recreate_database(url: str) -> bool:
    """Borra y crea la base `url` desde cero. Devuelve False si no hay servidor."""
    base, name = _split(url)
    try:
        admin = create_engine(f"{base}/postgres", isolation_level="AUTOCOMMIT")
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
            conn.execute(text(f'CREATE DATABASE "{name}"'))
        admin.dispose()
        return True
    except Exception:
        return False


def alembic_config(url: str) -> Config:
    cfg = Config(str(_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_ROOT / "alembic"))
    cfg.attributes["database_url"] = url
    cfg.attributes["configure_logging"] = False  # no reconfigurar el logging de pytest
    return cfg


def upgrade(url: str, revision: str = "head") -> None:
    command.upgrade(alembic_config(url), revision)


def downgrade(url: str, revision: str = "-1") -> None:
    command.downgrade(alembic_config(url), revision)
