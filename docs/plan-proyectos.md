# Plan: recurso Proyectos

Este documento registra la secuencia de incrementos acordada para implementar
el recurso Proyectos de TaskFlow. Cada incremento es confirmable por sí solo;
no se encadena el siguiente sin aprobación explícita.

Fuentes: `docs/contrato-api.md` (secciones Convenciones, Proyectos, Esquemas
de Respuesta y Matriz Mínima de Tests), `docs/decisiones-ingenieria.md`,
`CLAUDE.md`, `docs/plan-persistencia.md` (como precedente de forma y de
patrón de migración/tests), y el estado real del repositorio (`git log
--oneline`, árbol de `app/` y `tests/`, `alembic/versions/`).

## Estado de partida

- Código: `app/main.py` solo implementa `GET /health` y `GET /states`
  (conectado a Postgres). No existe ningún esquema, router ni consulta para
  proyectos (verificado: `grep -ri project` sobre `*.py` no encuentra nada).
- Infraestructura de persistencia ya resuelta por `docs/plan-persistencia.md`:
  `app/db.py` (engine async cacheado por event loop), `app/settings.py`
  (`get_database_url()` desde variables de entorno), y Alembic ya
  inicializado con una única migración, `53a19cbd0883` ("crea tabla de
  estados y siembra catalogo fijo"), sin revisión posterior. Las dependencias
  necesarias (SQLAlchemy async, asyncpg, Alembic) ya están en
  `pyproject.toml`; este plan no agrega ninguna nueva.
- Tests: `tests/test_health.py`, `tests/test_states.py`,
  `tests/test_migrations.py` (ciclo upgrade/downgrade de la migración de
  estados) y `tests/conftest.py` (fixture `db_connection`, una conexión async
  de vida corta por test contra Postgres real). Ningún test menciona
  proyectos.
- Contrato relevante (`## Proyectos`):
  - Campos mínimos: `id`, `name`, `description` opcional.
  - `POST /projects` → `201` con el recurso creado.
  - `GET /projects` → `200` con orden determinista: por `id` ascendente
    (`## Convenciones`, tabla "Orden de las listas").
  - `GET /projects/{id}` → `200`, o `404` si no existe.
  - `PATCH /projects/{id}` → `200` con actualización parcial.
  - `DELETE /projects/{id}` → `204` si no tiene tareas, `409` si las tiene;
    "no hay borrado en cascada implícito".
  - Esquema exacto (`## Esquemas de Respuesta`): `{"id": 1, "name": "Casa",
    "description": null}` — un campo opcional ausente se devuelve como
    `null`, nunca se omite; `GET` de colección devuelve una lista JSON en la
    raíz, no un objeto envolvente.
  - Matriz Mínima de Tests exige, entre otros: "CRUD feliz de proyectos",
    "IDs inexistentes", "Borrado de proyecto con tareas (409)", "Orden
    estable" y "Esquema de respuesta exacto".
- Decisiones de ingeniería relevantes: tests de persistencia contra Postgres
  real, nunca SQLite; el esquema cambia solo vía Alembic con
  `upgrade`/`downgrade` probados en ambos sentidos; una capacidad nueva
  arranca con un test que falla por su ausencia; no se debilita un test
  existente; nunca se abre `.env`.
- Decisión resuelta con el usuario antes de este plan: la tabla de tareas
  todavía no existe (es un incremento futuro, fuera de este alcance), así
  que el `409` de `DELETE /projects/{id}` por proyecto con tareas **no se
  implementa en este incremento**. El `DELETE` de este plan siempre borra y
  responde `204` (o `404` si el id no existe). El incremento de Tareas, al
  introducir la tabla `tasks` con `project_id`, es quien puede hacer valer
  el `409` real exigido por el contrato.

## Fuera de alcance

- Todo lo de `## Tareas v1` y `## Tareas v2: Fechas Límite`: no se crea tabla
  `tasks`, ni endpoints de tareas, ni `due_at`, ni filtros `project_id`/
  `state_id`/`overdue`.
- El `409` real de `DELETE /projects/{id}` por proyecto con tareas (ver
  decisión resuelta arriba): en este plan, `DELETE` siempre borra.
- Normalización Unicode de texto (categorías `Cc`, `Cf`, `Zl`, `Zp`, `Zs`):
  el contrato la exige explícitamente solo para `title` de tarea
  (`## Convenciones`, "Normalización de texto"), no para `name` ni
  `description` de proyecto. No se inventa una validación equivalente para
  proyectos que el contrato no pide.
- Seed o datos iniciales de proyectos: a diferencia de `states`, "Proyectos"
  no es un catálogo cerrado; los registros los crea la API, así que la
  migración de este plan no siembra filas.
- Skills, hooks, CI y cualquier cambio de dependencias
  (`pyproject.toml`/`uv.lock`).

## Incrementos

### Incremento 1 — Migración: tabla `projects`

Nueva migración Alembic, encadenada a la revisión actual `53a19cbd0883`, que
crea la tabla `projects` con `id` (entero, clave primaria autogenerada por la
base — "IDs enteros positivos generados por la base", `## Convenciones`),
`name` (string, no nulo) y `description` (string, nullable). Sin seed: a
diferencia de `states`, este recurso no es un catálogo cerrado. `downgrade`
simétrico que borra la tabla, siguiendo el mismo patrón que
`alembic/versions/53a19cbd0883_..._.py`.

**Comprobación**: test nuevo (amplía `tests/test_migrations.py` o agrega un
archivo análogo, sin debilitar los tests existentes de `states`) que valida,
contra Postgres real vía la fixture `db_connection`: base sin tabla
`projects` → `upgrade head` → la tabla existe con las columnas esperadas;
`downgrade` la revierte limpio. `uv run pytest -q tests/test_migrations.py`
en verde.

### Incremento 2 — Alta y lectura: `POST /projects`, `GET /projects`, `GET /projects/{id}`

Esquemas Pydantic del recurso Proyecto (`id`, `name`, `description` opcional
→ `null` si está ausente, nunca omitido). Implementación de:

- `POST /projects` → `201` con el recurso creado; `name` ausente responde
  `422` (comportamiento estándar de FastAPI/Pydantic para un campo
  requerido, sin normalización adicional no pedida por el contrato).
- `GET /projects` → `200`, lista ordenada por `id` ascendente.
- `GET /projects/{id}` → `200`, o `404` si no existe.

**Comprobación**: test nuevo `tests/test_projects.py` contra Postgres real,
con una fixture de tabla limpia por test (mismo patrón que
`catalogo_migrado` en `tests/test_states.py`: drop + `upgrade head` antes y
después de cada test), que cubra: creación feliz devuelve `201` con esquema
exacto (`{"id", "name", "description"}`, ni un campo de más); `GET /projects`
devuelve orden estable por `id` entre llamadas idénticas; `GET /projects/{id}`
existente devuelve `200`, inexistente devuelve `404`. `uv run pytest -q
tests/test_projects.py` y `uv run ruff check .` en verde.

### Incremento 3 — `PATCH /projects/{id}`

Actualización parcial: acepta `name` y/o `description` sin exigir ambos,
responde `200` con el recurso actualizado; `404` si el id no existe.

**Comprobación**: tests nuevos en `tests/test_projects.py` que cubran patch
de solo `name`, solo `description`, ambos a la vez, y `404` sobre un id
inexistente. `uv run pytest -q tests/test_projects.py` en verde.

### Incremento 4 — `DELETE /projects/{id}` (sin verificación de tareas)

`DELETE /projects/{id}` borra el proyecto y responde `204` sin cuerpo; `404`
si el id no existe. Por la decisión resuelta arriba, no verifica tareas
asociadas —la tabla `tasks` no existe todavía—, con un comentario en el
código que remite a esta decisión y al incremento de Tareas como responsable
del `409` real.

**Comprobación**: tests nuevos en `tests/test_projects.py`: `DELETE` de un
proyecto existente responde `204`, y un `GET /projects/{id}` posterior
responde `404`; `DELETE` de un id inexistente responde `404`. `uv run pytest
-q tests/test_projects.py` en verde.

### Verificación final del recurso completo

Tras el Incremento 4: `uv run pytest -q` y `uv run ruff check .` en verde
sobre todo el repositorio, incluyendo los tests de estados y migraciones ya
existentes.

## Reglas de ejecución

- Cada incremento queda en un estado confirmable por sí solo.
- No se encadena el siguiente incremento sin aprobación explícita.
- No se modifican `docs/contrato-api.md`, `docs/decisiones-ingenieria.md`,
  `CLAUDE.md`, `.gitignore` ni `.env`. No se abre `.env`.
- No se debilita una comprobación para conseguir verde.
