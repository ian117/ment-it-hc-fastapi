# Progreso y checklist

Documento vivo. Se actualiza al cerrar cada hito. Es también la base del
**checklist honesto** que pide el brief: si algo está pendiente, figura como
pendiente, no como hecho.

## Hitos

- [x] **Hito A — scaffolding + modelos + migraciones + auth** (commit `815bdeb`)
- [x] **Hito B — canales + despachador + notifications CRUD** (commit `1c75318`)
- [ ] **Hito C — Docker + e2e + README + checklist final** (pendiente)

## Criterios de aceptación (los 11 del brief)

| # | Criterio | Estado | Evidencia |
|---|----------|--------|-----------|
| 1 | Mismo email 2× → `409` las dos veces | ✅ | unique constraint en DB; probado con curl |
| 2 | Push sin token → `400` y nada escrito | ✅ | validación antes del INSERT; `total=0` confirmado |
| 3 | Push con token → `201`, `sent`, `sent_at` sellado | ✅ | probado con curl |
| 4 | `GET ?page=1&limit=5` → paginado, más nuevas primero | ✅ | orden `created_at desc, id desc`; techo `limit<=100` |
| 5 | Recurso ajeno → `404` (no 403) | ✅ | filtro por id + dueño en la misma query |
| 6 | Borrar propia → `204` sin body | ✅ | 0 bytes de body confirmado |
| 7 | Login fallido repetido → `429` | ✅ | slowapi, `5/minute` |
| 8 | Reset con email inexistente → misma respuesta | ✅ | mismo status/body que uno existente |
| 9 | Ninguna respuesta trae el hash | ✅ | se serializa contra `UserOut`, nunca el ORM |
| 10 | Migraciones reversibles, sin tipos huérfanos | ✅ | downgrade→base deja base limpia; re-upgrade reconstruye |
| 11 | `docker compose` desde clon limpio levanta todo | ⏳ | Hito C |

## Requisitos de calidad (sección 5 del brief)

- [x] 1. Unicidad de email ante registros concurrentes (constraint en DB)
- [x] 2. Migraciones versionadas y reversibles
- [x] 3. Hash nunca en respuestas
- [x] 4. Token de reset robado de la DB no alcanza (se guarda solo el hash)
- [x] 5. Auth no revela qué emails existen (login y reset genéricos)
- [x] 6. No se puede confirmar la existencia de un recurso ajeno (404)
- [x] 7. Resistencia a fuerza bruta (rate limit)
- [x] 8. Cabeceras de seguridad HTTP
- [x] 9. Forma única de error; validación conserva el campo; no filtra SQL
- [x] 10. Listado paginado, orden determinístico, techo de página
- [x] 11. Payload inválido para el canal se rechaza antes de escribir
- [x] 12. Envío fallido: motivo persistido y logueado
- [ ] 13. `docker compose` con healthchecks, red propia, migraciones antes del tráfico → **Hito C**
- [ ] 14. Imagen sin fuente de más / sin dev deps / no root / sin secretos → **Hito C**
- [x] 15. Tests unitarios sin DB (rápidos)  ·  [ ] e2e happy path contra DB real → **Hito C**

## Decisiones de diseño (resumen; el detalle va al README en Hito C)

- **SQLAlchemy 2.0 sync + psycopg3** (no async). Límite: proveedor real → async/outbox.
- **`channel` como texto libre** (sin ENUM nativo ni CHECK) para que sumar un canal no toque la DB.
- **`payload` en JSONB** → esquema agnóstico del canal.
- **argon2 (pwdlib)** para passwords; **reset token = SHA-256** en DB.
- **Contrato de canal con `abc.ABC`** (nominal) y no `Protocol` (estructural): quiero compartir comportamiento, no solo forma. Ver `channels/base.py`.
- **Validación de canal** en el schema Pydantic de cada canal + hook `validate_message`, ejecutada por el despachador antes de persistir.
- **El despachador dueña el orden invariante** (validar→persistir pending→entregar→registrar); los canales no tocan la DB → testeables sin base.
- **SMS >160 y email inválido**: se rechazan con `400`, no se truncan/aceptan en silencio.

## Estado operativo (dev)

- App dev: `uvicorn fastappi_notification.main:app` en `:8010` (docs en `/docs`).
- DB dev: contenedor `fastapi-notif-dev-db` (postgres:16-alpine) en `:5434`.
  Separado del contenedor del proyecto NestJS (`:5433`).
- Tests: `uv run pytest` — 15 unitarios en verde.

## Cómo retomar

1. Leer este archivo y `git log` para ubicarse.
2. Levantar DB dev y app (ver "Estado operativo").
3. Continuar por el próximo hito sin marcar (arriba).
