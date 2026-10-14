"""uuid ids, notifications.attempts/updated_at/payload.recipient, users.updated_at

F4 (ADR-012). Convierte `users.id`, `password_reset_tokens.id/user_id` y
`notifications.id/user_id` de integer a UUID conservando los datos (se generan
UUIDs y se remapean las FK). El downgrade vuelve a enteros secuenciales.

Revision ID: a3f1c9d27b40
Revises: d0eedf0b1855
Create Date: 2026-10-14 12:00:00

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f1c9d27b40"
down_revision: Union[str, Sequence[str], None] = "d0eedf0b1855"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CHILDREN = ("notifications", "password_reset_tokens")


def _run(*statements: str) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    # --- 1. Nuevas columnas UUID y remapeo de FK --------------------------------
    _run(
        "ALTER TABLE users ADD COLUMN id_new uuid NOT NULL DEFAULT gen_random_uuid()",
    )
    for table in CHILDREN:
        _run(
            f"ALTER TABLE {table} ADD COLUMN id_new uuid NOT NULL DEFAULT gen_random_uuid()",
            f"ALTER TABLE {table} ADD COLUMN user_id_new uuid",
            f"UPDATE {table} t SET user_id_new = u.id_new FROM users u WHERE t.user_id = u.id",
            f"ALTER TABLE {table} DROP CONSTRAINT {table}_user_id_fkey",
        )
    _run(
        "DROP INDEX ix_notifications_user_id",
        "DROP INDEX ix_password_reset_tokens_user_id",
    )

    # --- 2. Reemplazo de las columnas viejas -----------------------------------
    for table in ("users", *CHILDREN):
        _run(
            f"ALTER TABLE {table} DROP COLUMN id",  # arrastra la PK y su secuencia
            f"ALTER TABLE {table} RENAME COLUMN id_new TO id",
            f"ALTER TABLE {table} ALTER COLUMN id DROP DEFAULT",
            f"ALTER TABLE {table} ADD PRIMARY KEY (id)",
        )
    for table in CHILDREN:
        _run(
            f"ALTER TABLE {table} DROP COLUMN user_id",
            f"ALTER TABLE {table} RENAME COLUMN user_id_new TO user_id",
            f"ALTER TABLE {table} ALTER COLUMN user_id SET NOT NULL",
            f"ALTER TABLE {table} ADD CONSTRAINT {table}_user_id_fkey "
            "FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE",
        )
    _run("CREATE INDEX ix_password_reset_tokens_user_id ON password_reset_tokens (user_id)")

    # --- 3. Columnas nuevas ----------------------------------------------------
    _run(
        "ALTER TABLE users ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now()",
        "UPDATE users SET updated_at = created_at",
        "ALTER TABLE notifications ADD COLUMN attempts integer NOT NULL DEFAULT 0",
        "ALTER TABLE notifications ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now()",
        # Las ya entregadas o falladas tuvieron al menos un intento.
        "UPDATE notifications SET attempts = 1 WHERE status IN ('sent', 'failed')",
        "UPDATE notifications SET updated_at = COALESCE(sent_at, created_at)",
        # El dominio informa la hora; el default de BD solo sirvió para rellenar.
        "ALTER TABLE users ALTER COLUMN updated_at DROP DEFAULT",
        "ALTER TABLE notifications ALTER COLUMN updated_at DROP DEFAULT",
    )

    # --- 4. payload -> { "recipient": ... } ------------------------------------
    _run(
        """
        UPDATE notifications SET payload = jsonb_build_object(
            'recipient',
            COALESCE(payload->>'recipient', payload->>'email', payload->>'phone',
                     payload->>'device_token', '')
        )
        """
    )

    # --- 5. Índice de listado paginado determinístico ---------------------------
    _run(
        "CREATE INDEX ix_notifications_user_id_created_at_id "
        "ON notifications (user_id, created_at DESC, id DESC)"
    )


def downgrade() -> None:
    _run("DROP INDEX ix_notifications_user_id_created_at_id")

    # payload vuelve a las claves antiguas por canal.
    _run(
        """
        UPDATE notifications SET payload = CASE channel
            WHEN 'sms' THEN jsonb_build_object('phone', payload->>'recipient')
            WHEN 'push' THEN jsonb_build_object('device_token', payload->>'recipient')
            ELSE jsonb_build_object('recipient', payload->>'recipient')
        END
        """
    )

    _run(
        "ALTER TABLE notifications DROP COLUMN updated_at",
        "ALTER TABLE notifications DROP COLUMN attempts",
        "ALTER TABLE users DROP COLUMN updated_at",
    )

    # --- UUID -> enteros secuenciales (por antigüedad) ---------------------------
    for table in ("users", *CHILDREN):
        _run(
            f"ALTER TABLE {table} ADD COLUMN id_old integer",
            f"UPDATE {table} t SET id_old = r.n FROM "
            f"(SELECT id, row_number() OVER (ORDER BY created_at, id) AS n FROM {table}) r "
            "WHERE t.id = r.id",
        )
    for table in CHILDREN:
        _run(
            f"ALTER TABLE {table} ADD COLUMN user_id_old integer",
            f"UPDATE {table} t SET user_id_old = u.id_old FROM users u WHERE t.user_id = u.id",
            f"ALTER TABLE {table} DROP CONSTRAINT {table}_user_id_fkey",
        )
    _run("DROP INDEX ix_password_reset_tokens_user_id")

    for table in ("users", *CHILDREN):
        _run(
            f"ALTER TABLE {table} DROP COLUMN id",
            f"ALTER TABLE {table} RENAME COLUMN id_old TO id",
            f"ALTER TABLE {table} ALTER COLUMN id SET NOT NULL",
            f"ALTER TABLE {table} ADD PRIMARY KEY (id)",
            f"CREATE SEQUENCE {table}_id_seq AS integer OWNED BY {table}.id",
            f"ALTER TABLE {table} ALTER COLUMN id SET DEFAULT nextval('{table}_id_seq')",
            f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)",
        )
    for table in CHILDREN:
        _run(
            f"ALTER TABLE {table} DROP COLUMN user_id",
            f"ALTER TABLE {table} RENAME COLUMN user_id_old TO user_id",
            f"ALTER TABLE {table} ALTER COLUMN user_id SET NOT NULL",
            f"ALTER TABLE {table} ADD CONSTRAINT {table}_user_id_fkey "
            "FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE",
        )
    _run(
        "CREATE INDEX ix_notifications_user_id ON notifications (user_id)",
        "CREATE INDEX ix_password_reset_tokens_user_id ON password_reset_tokens (user_id)",
    )
