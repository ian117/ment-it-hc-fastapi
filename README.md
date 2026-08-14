# Sistema de Notificaciones — FastAPI

API REST para que usuarios autenticados gestionen y envíen notificaciones por
distintos canales (Email, SMS, Push). El envío es **simulado**: no se integra
ningún proveedor real. El foco del proyecto es el **diseño**: sumar un canal no
debe obligar a tocar la lógica de envío existente.

## Stack

- **Python 3.10 + FastAPI**
- **PostgreSQL** con **SQLAlchemy 2.0** (sync) y **psycopg3**
- **Alembic** para migraciones versionadas y reversibles
- **Pydantic v2** para validación
- **PyJWT** (tokens) y **pwdlib + argon2** (hashing)
- **slowapi** para rate limiting
- **uv** para dependencias y build
- **Docker / docker compose** para levantar todo

---

## Puesta en marcha

### Opción A — Docker (recomendada, no requiere instalar nada en el host)

```bash
docker compose up --build
```

Esto levanta tres servicios en una red propia:

1. `db` (PostgreSQL) con healthcheck.
2. `migrate`: corre `alembic upgrade head` y termina.
3. `app`: arranca **solo cuando las migraciones terminaron con éxito**, con su
   propio healthcheck en `/health`.

La API queda en `http://localhost:8000` (documentación en
`http://localhost:8000/docs`).

### Opción B — Desarrollo local

Requiere [uv](https://docs.astral.sh/uv/) y un PostgreSQL accesible.

```bash
# 1. Base de datos de desarrollo (ejemplo con Docker, en el puerto 5434)
docker run -d --name notif-dev-db \
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=notifications \
  -p 5434:5432 postgres:16-alpine

# 2. Dependencias
uv sync

# 3. Migraciones
uv run alembic upgrade head

# 4. Servidor
uv run uvicorn fastappi_notification.main:app --reload --port 8000
```

Copiá `.env.example` a `.env` para ajustar la configuración.

---

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5434/notifications` | Conexión a PostgreSQL (driver psycopg3). |
| `JWT_SECRET` | `dev-only-insecure-secret-change-me` | Secreto para firmar los JWT. **Obligatorio cambiarlo en producción.** |
| `JWT_ALGORITHM` | `HS256` | Algoritmo de firma. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Vigencia del token de acceso. |
| `RESET_TOKEN_EXPIRE_MINUTES` | `30` | Vigencia del token de reseteo. |
| `LOGIN_RATE_LIMIT` | `5/minute` | Umbral de fuerza bruta para el login. |

---

## Endpoints

Documentación navegable en `/docs` (Swagger) y `/redoc`.

### Autenticación

| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| `POST` | `/auth/register` | Registro con email y contraseña. `409` si el email ya existe. | — |
| `POST` | `/auth/login` | Devuelve un token de acceso. `429` al superar el umbral. | — |
| `POST` | `/auth/password-reset/request` | Solicita un reseteo. Responde igual exista o no el email. | — |
| `POST` | `/auth/password-reset/confirm` | Cambia la contraseña con un token válido. | — |

### Notificaciones (requieren `Authorization: Bearer <token>`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/notifications` | Crea una notificación y dispara el envío por su canal. |
| `GET` | `/notifications?page=1&limit=20` | Lista las propias, paginadas, más nuevas primero. |
| `GET` | `/notifications/{id}` | Consulta una propia. `404` si no existe o es ajena. |
| `PATCH` | `/notifications/{id}` | Modifica una propia (re-valida las reglas del canal). |
| `DELETE` | `/notifications/{id}` | Borra una propia. `204` sin body. |

**Payload de creación** — el objeto `payload` lleva los datos propios del canal:

```jsonc
// email
{ "title": "Hola", "content": "...", "channel": "email", "payload": { "recipient": "a@ex.com" } }
// sms   (content <= 160)
{ "title": "Hola", "content": "...", "channel": "sms",   "payload": { "phone": "+541112345678" } }
// push
{ "title": "Hola", "content": "...", "channel": "push",  "payload": { "device_token": "abc123" } }
```

---

## Tests

```bash
uv run pytest
```

- **Unitarios (rápidos, sin base):** `test_security.py` y `test_channels.py`.
- **End-to-end (happy path contra base real):** `test_e2e.py`. Crea/usa una base
  `notifications_test`; si no hay PostgreSQL disponible, el test se **omite**
  (skip) y la suite sigue verde. Se puede apuntar a otra base con
  `TEST_DATABASE_URL`.

Reversibilidad de migraciones (criterio de aceptación 10):

```bash
uv run alembic downgrade base   # deja la base sin tablas ni tipos huérfanos
uv run alembic upgrade head     # la reconstruye
```

---

## Decisiones de diseño (y sus límites)

### Contrato de canal: `abc.ABC`, no `typing.Protocol`

Elegí una **clase base abstracta** (tipado **nominal**) y no un `Protocol`
(tipado **estructural**) porque además del contrato quiero **compartir
comportamiento**: `validate()` es concreto en la base —parsea el payload contra
el esquema Pydantic de cada canal y unifica el error— y solo `deliver()` queda
abstracto. Con `Protocol` tendría el chequeo de forma pero cero reuso: cada canal
reimplementaría el parseo y la traducción del error. `Protocol` sería lo correcto
si aceptara objetos de terceros que no controlo; acá soy dueño de todos los
canales y quiero obligarlos a pasar por un mismo esqueleto. Con `Protocol` además
perdería la garantía de `ABC` de fallar al **instanciar** una subclase incompleta,
no recién al llamarla. Detalle en `channels/base.py`.

### El despachador dueña el orden; los canales no tocan la base

El orden invariante —validar → persistir en `pending` → entregar → registrar el
resultado— vive en `services/notifications.py`, no en los canales. Así un canal
**no puede** registrar un envío que nunca se validó, y como los canales operan
sobre datos planos (sin sesión de DB) se **testean sin levantar la base**.

### Dónde vive la validación específica de cada canal

En el **esquema Pydantic que cada canal declara** (`payload_schema`) más un hook
`validate_message` para reglas que exceden al payload (el largo del SMS). La
ejecuta el despachador **antes de abrir cualquier escritura**, así un payload
inválido devuelve `400` sin dejar nada en la base. Está co-ubicada con el canal:
"lo que cambia vive en cada canal".

### `channel` como texto libre, sin ENUM nativo ni CHECK

La columna `channel` es `VARCHAR` sin constraint de valores. La lista de canales
válidos vive en el **registry de la aplicación**, no en la base. Beneficio: sumar
un canal es un cambio 100% de código, sin migración.
**Límite conocido:** la base no impide, por sí sola, insertar un `channel`
inválido mediante un `INSERT` directo por fuera de la app; la integridad de ese
campo depende de la validación de la aplicación.

### `payload` en JSONB

Los datos propios de cada canal viven en una columna JSONB, no en columnas
tipadas. Mantiene el esquema **agnóstico del canal**: sumar un canal con otros
campos no altera la tabla.
**Límite conocido:** no hay validación a nivel de base sobre la forma del
`payload`; la garantiza la validación del canal.

### SQLAlchemy sync y la transacción sobre el envío

El guardado, el envío simulado y la actualización del estado corren en **una
sola transacción**. Esto se sostiene **solo porque el envío es simulado** (es
código en memoria, no una llamada de red).
**Límite conocido:** con un proveedor real no se mantiene una transacción
abierta sobre una llamada de red —bloquea una conexión del pool durante todo el
round-trip y un timeout se lleva puesta la transacción—. La forma correcta ahí
es *commitear en `pending` → enviar → actualizar el estado* (o un patrón outbox).
El estado `pending` ya existe para ese camino. Por lo mismo elegí sync sobre
async: sin I/O real que esperar, el manejo transaccional queda más simple.

### SMS > 160 y email inválido: se rechazan, no se degradan

Un SMS de más de 160 caracteres devuelve `400`; **no se trunca en silencio**.
Un email con destinatario inválido devuelve `400`. Perder o mutilar contenido
sin avisar es peor que fallar fuerte.

### `404` en vez de `403` para recursos ajenos

La consulta filtra por id **y** dueño en la misma cláusula, así "no existe" y "no
es tuyo" son indistinguibles desde afuera: un `403` le confirmaría al atacante
que el recurso existe.

### Un envío fallido devuelve `201`, no `5xx`

Si el payload era válido, la notificación se creó bien; lo que falla es la
entrega. Se devuelve `201` con estado `failed`, y el motivo queda **persistido y
logueado**. Los errores que sí son culpa del request se atajan antes con `400`.

### Seguridad de auth

- **Unicidad de email** garantizada por una constraint `UNIQUE` en la base, no
  por un chequeo en código: dos registros concurrentes no pueden colarse ambos.
- **Hash de contraseña** con argon2; nunca se serializa (las respuestas usan
  `UserOut`, que no tiene ese campo).
- **Token de reseteo**: en la base se guarda solo su `sha256`. Robar la fila no
  alcanza para resetear la contraseña.
  **Límite conocido:** el envío del token es simulado (se loguea); no hay
  integración real de email.
- **Login y reset** responden igual exista o no el email (no revelan qué emails
  están registrados). El registro sí devuelve `409` en duplicado, como pide el
  enunciado.
- **Rate limiting** en memoria por IP.
  **Límite conocido:** con varias réplicas hace falta un backend compartido
  (Redis) para que el conteo sea global y no por-proceso.
- **Cabeceras de seguridad HTTP** en todas las respuestas.

### Operación

- **`JWT_SECRET`** tiene un default de desarrollo para que un clon limpio levante
  sin fricción.
  **Límite conocido:** en producción hay que pasar un secreto propio; el default
  es inseguro a propósito.

---

## Autoevaluación

1. **¿Qué archivos tocarías para agregar WhatsApp?** Un archivo nuevo
   `channels/whatsapp.py` con `@register class WhatsAppChannel(Channel)` (su
   `payload_schema` y su `deliver`) y un import en `channels/__init__.py`. Nada
   más: ni el despachador, ni el router, ni los modelos, ni la base.
2. **¿Por qué `ABC` y no `Protocol`?** Ver arriba: quiero compartir
   comportamiento, no solo forma, y la garantía de instanciación de `ABC`.
3. **¿Y si el proveedor tarda 30s?** Con el diseño actual (transacción sobre el
   envío) dolería primero en el pool de conexiones. Por eso está documentado el
   camino correcto para un proveedor real: `pending` → enviar → actualizar.
4. **¿Cómo probás un canal sin base?** Los canales son puros: `test_channels.py`
   los ejercita en memoria, sin sesión de DB.
5. **¿Qué cambiaría para producción?** Sacar la transacción de alrededor del
   envío (outbox), mover el rate limit a Redis, e integrar un envío de email real
   para los tokens de reseteo.

---

## Checklist

El estado detallado (hitos y criterios) vive en [`PROGRESS.md`](PROGRESS.md), y
se mantiene honesto: lo pendiente figura como pendiente.
