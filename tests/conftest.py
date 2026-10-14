"""Fixtures para el test end-to-end contra una base real.

Toda la conexión vive dentro de fixtures (nunca a nivel de import), así los
tests unitarios corren sin base y no disparan nada de esto.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.db_utils import TEST_DATABASE_URL, recreate_database, upgrade


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """El limiter es en memoria y global: cada test parte con los contadores en cero."""
    from fastappi_notification.core.limiter import limiter

    limiter.reset()
    yield


@pytest.fixture(scope="session")
def migrated_database() -> str:
    """Base de tests limpia con el esquema construido por `alembic upgrade head`."""
    if not recreate_database(TEST_DATABASE_URL):
        pytest.skip("PostgreSQL de tests no disponible; se omite el e2e")
    upgrade(TEST_DATABASE_URL)
    return TEST_DATABASE_URL


@pytest.fixture(scope="session")
def client(migrated_database):
    # Importes tardíos: recién acá tocamos la app y la base.
    from fastapi.testclient import TestClient

    from fastappi_notification.core.db import get_db
    from fastappi_notification.main import app

    engine = create_engine(migrated_database)
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
    engine.dispose()


class UserSession:
    """Usuario registrado por la API, con su JWT y cabeceras listas."""

    def __init__(self, id: str, email: str, headers: dict[str, str]) -> None:
        self.id = id
        self.email = email
        self.headers = headers


@pytest.fixture
def make_user(client):
    """Fábrica de usuarios: registra por la API y emite el JWT directamente.

    El login real está limitado a 5/min por IP (slowapi), así que solo un test
    pasa por `/auth/login`; el resto evita agotar ese límite.
    """
    import uuid

    from fastappi_notification import container

    def _make() -> UserSession:
        email = f"user-{uuid.uuid4().hex[:12]}@example.com"
        r = client.post("/auth/register", json={"email": email, "password": "secret12345"})
        assert r.status_code == 201, r.text
        user_id = r.json()["id"]
        token = container.token_issuer.issue(uuid.UUID(user_id)).access_token
        return UserSession(user_id, email, {"Authorization": f"Bearer {token}"})

    return _make


@pytest.fixture
def db_session(migrated_database):
    """Sesión SQLAlchemy directa sobre la base de tests migrada (para repositorios y SQL crudo)."""
    engine = create_engine(migrated_database)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
