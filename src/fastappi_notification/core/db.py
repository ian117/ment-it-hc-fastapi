from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    """Base declarativa. Todos los modelos heredan de acá y su metadata es
    la que Alembic usa para generar migraciones."""


_settings = get_settings()

# `pool_pre_ping` evita servir conexiones muertas tras un reinicio de la base.
engine = create_engine(_settings.database_url, pool_pre_ping=True)

# `expire_on_commit=False`: tras un commit los objetos siguen accesibles sin
# emitir un nuevo SELECT. Cómodo para leer atributos después de guardar.
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Dependencia de FastAPI: abre una sesión por request y la cierra al final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
