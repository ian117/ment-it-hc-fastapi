"""Las migraciones suben, bajan y vuelven a subir sobre una base limpia (PostgreSQL real)."""

import pytest
from sqlalchemy import create_engine, inspect

from tests.db_utils import MIGRATION_DATABASE_URL, downgrade, recreate_database, upgrade

TABLES = {"users", "password_reset_tokens", "notifications"}


def _tables(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names()) - {"alembic_version"}
    finally:
        engine.dispose()


def test_upgrade_downgrade_upgrade_round_trip():
    if not recreate_database(MIGRATION_DATABASE_URL):
        pytest.skip("PostgreSQL de tests no disponible; se omite el test de migraciones")

    upgrade(MIGRATION_DATABASE_URL)
    assert _tables(MIGRATION_DATABASE_URL) == TABLES

    downgrade(MIGRATION_DATABASE_URL, "-1")
    upgrade(MIGRATION_DATABASE_URL)
    assert _tables(MIGRATION_DATABASE_URL) == TABLES
