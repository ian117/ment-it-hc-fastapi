"""Fixtures para el test end-to-end contra una base real.

Toda la conexión vive dentro de fixtures (nunca a nivel de import), así los
tests unitarios de `test_security.py` y `test_channels.py` corren sin base y no
disparan nada de esto.
"""

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Base de tests separada de la de desarrollo para no pisar datos.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5434/notifications_test",
)


def _server_url(db_url: str) -> str:
    # Misma conexión pero contra la base administrativa 'postgres'.
    base, _, _ = db_url.rpartition("/")
    return f"{base}/postgres"


def _ensure_test_database() -> bool:
    """Crea la base de tests si falta. Devuelve False si el servidor no está."""
    try:
        admin = create_engine(_server_url(TEST_DATABASE_URL), isolation_level="AUTOCOMMIT")
        target = TEST_DATABASE_URL.rsplit("/", 1)[-1]
        with admin.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": target}
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{target}"'))
        admin.dispose()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def client():
    if not _ensure_test_database():
        pytest.skip("PostgreSQL de tests no disponible; se omite el e2e")

    # Importes tardíos: recién acá tocamos la app y la base.
    from fastapi.testclient import TestClient

    from fastappi_notification.core.db import Base, get_db
    from fastappi_notification.main import app
    import fastappi_notification.models  # noqa: F401  (registra las tablas)

    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()
