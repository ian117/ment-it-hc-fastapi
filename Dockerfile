# syntax=docker/dockerfile:1

# ---- builder -------------------------------------------------------------
# Instala dependencias y compila el proyecto en un venv aislado. Acá viven uv y
# las herramientas de build; nada de esto llega a la imagen final.
FROM python:3.10-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Primero solo los manifests: si no cambian, esta capa (la pesada) se cachea.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Ahora el código y el proyecto, instalado NO editable: la fuente queda copiada
# dentro del site-packages del venv, no referenciada desde /app/src.
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# ---- runtime -------------------------------------------------------------
# Solo el venv + las migraciones. Sin uv, sin dev deps, sin herramientas de
# compilación, sin código fuente crudo. Corre como usuario sin privilegios.
FROM python:3.10-slim-bookworm AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
# Las migraciones sí son necesarias en runtime: el servicio `migrate` las corre.
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app alembic.ini ./

USER app

EXPOSE 8000

CMD ["uvicorn", "fastappi_notification.main:app", "--host", "0.0.0.0", "--port", "8000"]
