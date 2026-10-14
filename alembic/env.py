from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from fastappi_notification.core.config import get_settings
from fastappi_notification.core.db import Base

# Importar los modelos registra sus tablas en Base.metadata (necesario para
# que autogenerate las "vea").
import fastappi_notification.models  # noqa: F401

config = context.config

# La URL de la base la manda la app, no el .ini: una sola fuente de verdad y
# funciona igual en local y en Docker.
# Los tests pasan su propia URL (y piden no tocar el logging) vía `config.attributes`.
_url_override = config.attributes.get("database_url")
config.set_main_option(
    "sqlalchemy.url", (_url_override or get_settings().database_url).replace("%", "%%")
)

if config.config_file_name is not None and config.attributes.get("configure_logging", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
