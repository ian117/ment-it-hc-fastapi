"""auth: users.password_hash, password_reset_tokens.used_at y token_hash char(64)

F7 (ADR-014). Deja `users` y `password_reset_tokens` con el esquema del diseño (sección 5):
- users.hashed_password (varchar) -> password_hash (text); emails en minúsculas (el dominio
  normaliza); sin DEFAULT en created_at (la hora la pone el dominio).
- password_reset_tokens.used (boolean) -> used_at (timestamptz; los usados toman created_at);
  token_hash varchar(64) -> char(64); sin DEFAULT en created_at.
Los datos se conservan. El downgrade restaura el esquema anterior sin tipos huérfanos.

Revision ID: b7c2e5a81f36
Revises: a3f1c9d27b40
Create Date: 2026-10-14 18:00:00

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c2e5a81f36"
down_revision: Union[str, Sequence[str], None] = "a3f1c9d27b40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _run(*statements: str) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _run(
        # users
        "ALTER TABLE users RENAME COLUMN hashed_password TO password_hash",
        "ALTER TABLE users ALTER COLUMN password_hash TYPE text",
        # El dominio guarda el email en minúsculas; se normalizan los existentes salvo que
        # choquen con otro ya normalizado (quedan tal cual en vez de romper la migración).
        "UPDATE users u SET email = lower(u.email) WHERE u.email <> lower(u.email) "
        "AND NOT EXISTS (SELECT 1 FROM users o WHERE o.email = lower(u.email))",
        "ALTER TABLE users ALTER COLUMN created_at DROP DEFAULT",
        # password_reset_tokens
        "ALTER TABLE password_reset_tokens ADD COLUMN used_at timestamptz",
        "UPDATE password_reset_tokens SET used_at = created_at WHERE used",
        "ALTER TABLE password_reset_tokens DROP COLUMN used",
        "ALTER TABLE password_reset_tokens ALTER COLUMN token_hash TYPE char(64)",
        "ALTER TABLE password_reset_tokens ALTER COLUMN created_at DROP DEFAULT",
    )


def downgrade() -> None:
    _run(
        "ALTER TABLE password_reset_tokens ALTER COLUMN created_at SET DEFAULT now()",
        "ALTER TABLE password_reset_tokens ALTER COLUMN token_hash TYPE varchar(64)",
        "ALTER TABLE password_reset_tokens ADD COLUMN used boolean NOT NULL DEFAULT false",
        "UPDATE password_reset_tokens SET used = true WHERE used_at IS NOT NULL",
        "ALTER TABLE password_reset_tokens ALTER COLUMN used DROP DEFAULT",
        "ALTER TABLE password_reset_tokens DROP COLUMN used_at",
        "ALTER TABLE users ALTER COLUMN created_at SET DEFAULT now()",
        "ALTER TABLE users ALTER COLUMN password_hash TYPE varchar",
        "ALTER TABLE users RENAME COLUMN password_hash TO hashed_password",
    )
