"""Las migraciones suben, bajan y vuelven a subir sobre una base limpia (PostgreSQL real)."""

import uuid

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text

from tests.db_utils import (
    MIGRATION_DATABASE_URL,
    alembic_config,
    downgrade,
    recreate_database,
    upgrade,
)

TABLES = {"users", "password_reset_tokens", "notifications"}
BEFORE_AUTH = "a3f1c9d27b40"  # esquema previo a la migración de auth (F7)


def _tables(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names()) - {"alembic_version"}
    finally:
        engine.dispose()


def _columns(url: str, table: str) -> dict[str, str]:
    engine = create_engine(url)
    try:
        return {c["name"]: str(c["type"]) for c in inspect(engine).get_columns(table)}
    finally:
        engine.dispose()


def _fresh_database() -> None:
    if not recreate_database(MIGRATION_DATABASE_URL):
        pytest.skip("PostgreSQL de tests no disponible; se omite el test de migraciones")


def test_upgrade_downgrade_upgrade_round_trip():
    _fresh_database()

    upgrade(MIGRATION_DATABASE_URL)
    assert _tables(MIGRATION_DATABASE_URL) == TABLES

    downgrade(MIGRATION_DATABASE_URL, "-1")
    upgrade(MIGRATION_DATABASE_URL)
    assert _tables(MIGRATION_DATABASE_URL) == TABLES


def test_models_and_migrations_have_no_differences():
    _fresh_database()
    upgrade(MIGRATION_DATABASE_URL)
    command.check(alembic_config(MIGRATION_DATABASE_URL))  # lanza si autogenerate detecta cambios


def test_auth_migration_converts_columns_and_keeps_data_both_ways():
    _fresh_database()
    upgrade(MIGRATION_DATABASE_URL, BEFORE_AUTH)

    user_id, used_id, fresh_id = (str(uuid.uuid4()) for _ in range(3))
    used_hash, fresh_hash = "a" * 64, "b" * 64
    engine = create_engine(MIGRATION_DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, created_at, updated_at) "
                "VALUES (:id, 'Legacy.User@Example.com', '$argon2id$legacy', '2026-01-01 10:00+00', '2026-01-01 10:00+00')"
            ),
            {"id": user_id},
        )
        for token_id, token_hash, used in ((used_id, used_hash, True), (fresh_id, fresh_hash, False)):
            conn.execute(
                text(
                    "INSERT INTO password_reset_tokens (id, user_id, token_hash, expires_at, used, created_at) "
                    "VALUES (:id, :u, :h, '2030-01-01 00:00+00', :used, '2026-01-02 09:00+00')"
                ),
                {"id": token_id, "u": user_id, "h": token_hash, "used": used},
            )

    upgrade(MIGRATION_DATABASE_URL)

    users = _columns(MIGRATION_DATABASE_URL, "users")
    assert "password_hash" in users and "hashed_password" not in users
    assert users["password_hash"] == "TEXT"
    tokens = _columns(MIGRATION_DATABASE_URL, "password_reset_tokens")
    assert "used_at" in tokens and "used" not in tokens
    assert tokens["token_hash"] == "CHAR(64)"
    with engine.connect() as conn:
        user = conn.execute(text("SELECT email, password_hash FROM users WHERE id = :id"), {"id": user_id}).one()
        assert user.password_hash == "$argon2id$legacy"
        assert user.email == "legacy.user@example.com"  # el dominio normaliza a minúsculas
        rows = {
            r.id: r
            for r in conn.execute(text("SELECT id::text AS id, used_at, created_at FROM password_reset_tokens"))
        }
        assert rows[used_id].used_at == rows[used_id].created_at  # los usados toman created_at
        assert rows[fresh_id].used_at is None

    downgrade(MIGRATION_DATABASE_URL, "-1")

    users = _columns(MIGRATION_DATABASE_URL, "users")
    assert "hashed_password" in users and "password_hash" not in users
    tokens = _columns(MIGRATION_DATABASE_URL, "password_reset_tokens")
    assert "used" in tokens and "used_at" not in tokens
    assert tokens["token_hash"] == "VARCHAR(64)"
    with engine.connect() as conn:
        used = {
            r.id: r.used
            for r in conn.execute(text("SELECT id::text AS id, used FROM password_reset_tokens"))
        }
        assert used == {used_id: True, fresh_id: False}
        assert conn.execute(text("SELECT hashed_password FROM users")).scalar_one() == "$argon2id$legacy"

    upgrade(MIGRATION_DATABASE_URL)  # vuelve a subir sin errores sobre datos ya convertidos
    engine.dispose()
