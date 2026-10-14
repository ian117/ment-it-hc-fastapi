# fastappi-notification

Implementación en FastAPI del diseño compartido (`../docs/diseno-notificaciones.md`). Las reglas comunes viven en `../CLAUDE.md`.

## Stack

Python 3.10 · FastAPI · SQLAlchemy 2.0 (sync, psycopg3) · Alembic · Pydantic v2 · PyJWT · pwdlib + argon2 · slowapi · pytest · uv

## Comandos

```bash
docker run -d --name notif-dev-db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=notifications -p 5434:5432 postgres:16-alpine   # Postgres de desarrollo (:5434)
uv sync
uv run alembic upgrade head
uv run uvicorn fastappi_notification.main:app --reload --port 8000   # /docs y /openapi.json
uv run pytest                        # unitarios + e2e (el e2e se omite si no hay Postgres)
uv run alembic revision --autogenerate -m "mensaje"
uv run alembic downgrade -1
docker compose up --build            # todo containerizado (db + migrate + app)
```

## Estructura (hexagonal)

```
src/fastappi_notification/
  domain/           # dataclasses y excepciones propias. Sin fastapi, sqlalchemy ni pydantic.
  application/      # casos de uso + puertos (abc.ABC / Protocol)
  infrastructure/
    persistence/    # modelos SQLAlchemy, mappers, repositorios
    channels/       # ChannelGateway por canal (simulados)
    security/       # Argon2Hasher, JwtTokenIssuer
  api/              # routers, esquemas Pydantic (camelCase vía alias_generator), handlers de Problem Details
  container.py      # raíz de composición; deps.py solo expone Depends()
  main.py
```

## Convenciones

- Pydantic vive solo en `api/` (y en configuración); el dominio usa dataclasses.
- El JSON se expone en camelCase y el código es snake_case (`alias_generator=to_camel`, `populate_by_name=True`).
- Los errores de validación de request devuelven 400 (se sobrescribe el 422 por defecto de FastAPI).
- Toda migración debe poder hacer `downgrade` sin dejar tipos huérfanos.

## Estado respecto al diseño

Sin pendientes: el stack implementa el diseño completo (notificaciones y auth) y cumple `../contract/openapi.yaml`. Las decisiones están en `../docs/adr/` (001–014). Si el diseño cambia, se corrige primero allí.
