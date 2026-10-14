# Sistema de Notificaciones — FastAPI

API REST para que usuarios autenticados creen y envíen notificaciones por email, SMS y push. La entrega es **simulada**: no hay proveedores reales. Es la implementación FastAPI del diseño compartido con la versión NestJS: mismo contrato HTTP ([`../contract/openapi.yaml`](../contract/openapi.yaml)), mismo dominio y mismo esquema de base de datos. El diseño está en [`../docs/diseno-notificaciones.md`](../docs/diseno-notificaciones.md) y las decisiones en [`../docs/adr/`](../docs/adr/).

## Stack

Python 3.10 · FastAPI · SQLAlchemy 2.0 (sync, psycopg3) · Alembic · Pydantic v2 · PyJWT · pwdlib + argon2 · slowapi · PostgreSQL 16 · pytest · uv · Docker Compose

## Estructura (hexagonal, ADR-001)

```
src/fastappi_notification/
  domain/          # entidades (User, PasswordResetToken, Notification), Email, políticas de canal,
                   # errores de dominio. Dataclasses; sin fastapi, sqlalchemy ni pydantic.
  application/     # casos de uso, puertos (repositorios, Clock, IdGenerator, hasher, emisor de tokens)
                   # y registro de gateways
  infrastructure/
    persistence/   # modelos SQLAlchemy, mappers y repositorios (el modelo ORM nunca sale de aquí)
    channels/      # gateways simulados de email, sms y push
    security/      # Argon2PasswordHasher, JwtTokenIssuer/Verifier, generador de tokens de reseteo
    clock.py       # SystemClock y UuidIdGenerator
  api/             # routers, esquemas Pydantic (camelCase), dependencias, Problem Details, OpenAPI
  core/            # settings, engine/sesión, rate limiter (slowapi), cabeceras de seguridad
  container.py     # raíz de composición: único lugar que conoce las clases concretas
  main.py          # create_app() y /health
alembic/           # migraciones
tests/             # domain/, application/, infrastructure/, api/ y e2e
```

`api/deps.py` solo expone `Depends()`; el cableado real vive en `container.py`. Los routers únicamente traducen HTTP a casos de uso.

## Puesta en marcha

### Docker (no requiere nada en el host)

```bash
docker compose up --build
```

Levanta `db` (PostgreSQL con healthcheck), `migrate` (corre `alembic upgrade head` y termina) y `app`, que arranca solo cuando las migraciones terminaron. API en `http://localhost:8000` (`/docs`, `/openapi.json`, `/health`). El servicio `app` recibe `DATABASE_URL` y `JWT_SECRET`; el resto de variables usa sus defaults.

Variables del compose (opcionales): `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `JWT_SECRET`, `APP_PORT`.

### Local

Requiere [uv](https://docs.astral.sh/uv/) y Docker para la base.

```bash
docker run -d --name fastapi-notif-dev-db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=notifications -p 5434:5432 postgres:16-alpine   # Postgres de desarrollo en :5434
uv sync
uv run alembic upgrade head
uv run uvicorn fastappi_notification.main:app --reload --port 8000
```

Copia `.env.example` a `.env` para cambiar la configuración (los defaults ya apuntan a `localhost:5434`).

### Variables de entorno

Se leen en `src/fastappi_notification/core/config.py` (entorno o `.env`).

| Variable | Default | Efecto |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5434/notifications` | Conexión a PostgreSQL (psycopg3). La usan la app y Alembic. |
| `JWT_SECRET` | `dev-only-insecure-secret-change-me` | Firma de los JWT (HS256). Con `ENVIRONMENT=production` es obligatorio uno propio de ≥ 32 caracteres: si no, la app no arranca (ADR-015). Genera uno con `openssl rand -hex 32`. |
| `JWT_ALGORITHM` | `HS256` | Algoritmo de firma. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Vigencia del JWT; `expiresIn` = minutos × 60. |
| `RESET_TOKEN_EXPIRE_MINUTES` | `15` | Vigencia del token de reseteo de contraseña. |
| `ENVIRONMENT` | `development` | Si es `production`, `POST /auth/password-reset/request` nunca devuelve `resetToken`. Con cualquier otro valor lo devuelve cuando el email existe. |
| `LOGIN_RATE_LIMIT` | `5/minute` | Límite por IP de `POST /auth/login` (formato slowapi). |
| `RESET_REQUEST_RATE_LIMIT` | `5/minute` | Límite por IP de `POST /auth/password-reset/request`. |

Solo para tests: `TEST_DATABASE_URL` (default `postgresql+psycopg://postgres:postgres@localhost:5434/notifications_test`).

## Endpoints

JSON en camelCase. Los endpoints de notificaciones requieren `Authorization: Bearer <accessToken>` y siempre operan sobre las notificaciones del usuario autenticado. Cualquier ruta protegida sin token válido responde `401`.

| Método | Ruta | Éxito | Errores |
|---|---|---|---|
| POST | `/auth/register` | 201 `{id, email, createdAt}` | 400, 409 |
| POST | `/auth/login` | 200 `{accessToken, tokenType: "Bearer", expiresIn}` | 400, 401, 429 |
| GET | `/auth/me` | 200 `{id, email, createdAt}` | 401 |
| POST | `/auth/password-reset/request` | 202 `{message}` (+ `resetToken` si aplica) | 400, 429 |
| POST | `/auth/password-reset/confirm` | 200 `{message}` | 400 |
| POST | `/notifications` | 201 `Notification` (`status` `sent` o `failed`) | 400, 401 |
| GET | `/notifications?page=1&limit=20` | 200 `{data, total, page, limit}`, más nuevas primero, `limit ≤ 100` | 400, 401 |
| GET | `/notifications/{id}` | 200 `Notification` | 401, 404 |
| PATCH | `/notifications/{id}` | 200 `Notification` tras el reenvío | 400, 401, 404, 409 |
| DELETE | `/notifications/{id}` | 204 | 401, 404 |

Creación y edición (en el PATCH todos los campos son opcionales y `channel` no se acepta):

```json
{ "title": "Hola", "content": "...", "channel": "sms", "payload": { "recipient": "+5219611234567" } }
```

El esquema navegable y generado por la app está en `/docs` y `/openapi.json`.

### Errores: Problem Details (RFC 9457, ADR-006/012/014)

Todos los errores son `application/problem+json`; `type` es `https://errors.local/<slug>` y `instance` es la ruta de la request. Nunca se exponen trazas ni detalles internos. La validación de request devuelve **400** (no el 422 de FastAPI), con `errors[].field` en notación de puntos.

```json
{
  "type": "https://errors.local/notification-not-editable",
  "title": "Notification not editable",
  "status": 409,
  "detail": "Only failed notifications can be edited",
  "instance": "/notifications/3f1c…"
}
```

Slugs: `validation-error`, `unknown-channel`, `channel-rule-violation` (400); `unauthorized` (401); `notification-not-found`, `not-found` (404); `notification-not-editable`, `email-already-registered` (409); `invalid-reset-token` (400); `too-many-requests` (429); `internal-error` (500).

## Reglas de dominio observables

- Estados de `Notification`: `pending` → `sent` (terminal) o `failed`. Solo se edita una notificación en `failed`; editar vuelve a `pending` y reenvía (ADR-007, ADR-009). Cualquier otro estado responde `409`. El canal no cambia nunca: para otro canal se crea otra notificación.
- Borrar se permite en cualquier estado.
- Una notificación ajena o inexistente (o con un id que no es UUID) responde `404`, nunca `403`.
- Un payload que viola las reglas del canal responde `400` y no escribe nada. SMS: destinatario E.164 y `content` ≤ 160 caracteres (se rechaza, no se trunca). Email: destinatario válido. Push: device token no vacío con formato válido (ADR-010).
- Si el payload es válido pero la entrega falla, la respuesta es `201` con `status: "failed"`, `attempts` incrementado y `errorMessage`.

## Flujo de envío sin transacción abierta (ADR-008)

Crear y editar comparten el mismo final: la política del canal valida y formatea el mensaje; se guarda la notificación en `pending` (commit); se entrega por el gateway **fuera de cualquier transacción**; se marca `sent` o `failed` y se guarda de nuevo (commit). Si el proceso cae entre medias, queda un `pending` recuperable. Cada `save` del repositorio es una transacción corta.

## Canales

Una `ChannelPolicy` (dominio) valida y da formato; un `ChannelGateway` (infraestructura) entrega (ADR-005). Para agregar un canal, por ejemplo WhatsApp: una `WhatsAppPolicy` en `domain/channels/`, un `WhatsAppGateway` en `infrastructure/channels/` y registrar ambos en `container.py` (`policies` y `gateways`). No cambian casos de uso, routers ni migraciones (`channel` es `varchar`, ADR-004).

Gateways simulados (deterministas, ADR-012): `email` y `push` fallan si el destinatario en minúsculas contiene `fail`; `sms` falla si el destinatario termina en `0000`. El resto entrega con éxito. El fallo informa `Simulated delivery failure` y cada entrega queda en el log.

## Seguridad

- Contraseñas con **argon2** (pwdlib); el hash nunca sale en una respuesta.
- JWT HS256 **sin estado**: la dependencia de usuario actual valida firma, expiración, tipo y `sub`, sin consultar la base; solo `/auth/me` lee el usuario.
- Reseteo de contraseña: en base solo se guarda el `sha256` del token, que se usa una única vez y vence a los 15 minutos. El token en claro nunca se escribe en el log. Fuera de producción, `resetToken` viaja en la respuesta (no hay canal de email todavía).
- Anti-enumeración: el reseteo responde igual exista o no el email, y un login fallido no revela cuál dato falló.
- Rate limit de `POST /auth/login` y `POST /auth/password-reset/request`: 5 por minuto por IP → `429`. Es **en memoria con slowapi, es decir por proceso**; con varias réplicas haría falta un backend compartido.
- Cabeceras de seguridad HTTP en todas las respuestas.

## Migraciones

```bash
uv run alembic upgrade head      # aplica
uv run alembic downgrade -1      # revierte la última
uv run alembic check             # verifica que los modelos no difieren de las migraciones
uv run alembic revision --autogenerate -m "mensaje"
```

Toda migración debe ser reversible y no dejar tipos huérfanos. El esquema es el de la sección 5 del diseño.

## Tests

```bash
uv run pytest
```

- **Sin base:** `tests/domain/`, `tests/application/` (fakes en memoria), `tests/infrastructure/` y `tests/api/`.
- **Con PostgreSQL:** `test_migrations.py`, `test_auth_repositories.py` y los e2e `test_auth_e2e.py` y `test_notifications_e2e.py`. Usan las bases `notifications_test` y `notifications_test_migrations` en el servidor de `TEST_DATABASE_URL` (por defecto `localhost:5434`), que se recrean en cada ejecución con el esquema real de Alembic. Si no hay servidor, esos tests se **omiten** (skip) y la suite sigue en verde.

## Más documentación

Decisiones de arquitectura (001–014), diseño y contrato: [`../docs/adr/`](../docs/adr/), [`../docs/diseno-notificaciones.md`](../docs/diseno-notificaciones.md).
