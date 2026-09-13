# Plan: recurso Tareas (v1 y v2: Fechas Límite)

Este documento registra la secuencia de incrementos acordada para implementar
el recurso Tareas de TaskFlow, versiones v1 y v2 completas. Cada incremento
es confirmable por sí solo; no se encadena el siguiente sin aprobación
explícita.

Fuentes: `docs/contrato-api.md` (secciones Convenciones, Tareas v1, Tareas
v2: Fechas Límite, Esquemas de Respuesta y Matriz Mínima de Tests),
`docs/decisiones-ingenieria.md`, `CLAUDE.md`, `docs/plan-proyectos.md` (de
donde viene el compromiso pendiente que cierra el Incremento 2 de este
plan), `docs/plan-persistencia.md` (precedente de forma), y el estado real
del repositorio (`git log --oneline`, árbol de `app/`, `tests/` y
`alembic/versions/`, `uv run alembic current`).

## Estado de partida

- Código: `app/main.py` implementa `GET /health`, `GET /states` y el CRUD
  completo de Proyectos (`POST`, `GET` lista, `GET` por id, `PATCH`,
  `DELETE`). El `DELETE /projects/{id}` de hoy siempre borra y responde
  `204`: `docs/plan-proyectos.md` documentó explícitamente que el `409` de
  "proyecto con tareas" queda diferido "al incremento de Tareas, que
  introduce la FK `project_id` necesaria para detectarlo". No existe
  ningún esquema, endpoint, migración ni test de Tareas (verificado:
  `grep -ri task` sobre `*.py` solo encuentra "TaskFlow"/"taskflow" y el
  comentario que ya anuncia este mismo diferimiento).
- Infraestructura: dos migraciones aplicadas, cabeza en `fd59bbd33189`
  (`uv run alembic current`): `53a19cbd0883` (tabla `states` + seed) y
  `fd59bbd33189` (tabla `projects`, sin FK entrantes todavía).
- Tests: `test_health.py`, `test_states.py`, `test_migrations.py`,
  `test_projects.py`, y `tests/conftest.py` con `db_connection`,
  `reset_schema(tablas=("projects","states"))` y `run_alembic`
  centralizados. Ningún test menciona tareas.
- Contrato relevante:
  - `## Tareas v1`: campos `id`, `title`, `description` opcional,
    `project_id`, `state_id`. `POST /tasks` → `201`, valida proyecto,
    estado y título. `GET /tasks` → `200`, admite `project_id` y
    `state_id` solos o combinados. `GET /tasks/{id}` → `200` o `404`.
    `PATCH /tasks/{id}` → `200` con actualización parcial consistente.
    `DELETE /tasks/{id}` → `204` sin cuerpo.
  - `## Tareas v2: Fechas Límite`: `due_at` opcional, con zona horaria,
    normalizado a UTC; omitirlo conserva compatibilidad v1; una fecha sin
    zona se rechaza con `422`. `GET /tasks?overdue=true` devuelve tareas
    con `due_at` anterior al instante de evaluación y estado distinto de
    `HECHA`; una tarea sin fecha no está vencida. Fuera de alcance
    (declarado por el propio contrato): recordatorios, scheduler, zona
    preferida del usuario, cambio automático de estado.
  - `## Convenciones`: normalización de texto aplicada a `title` de tarea
    (recorte + rechazo con `422` si no queda ningún carácter visible,
    por categoría Unicode `Cc`, `Cf`, `Zl`, `Zp`, `Zs`); orden de
    `GET /tasks` por `id` ascendente, también con filtros aplicados; "una
    referencia a proyecto o estado inexistente no se crea implícitamente".
  - `## Esquemas de Respuesta`: Tarea (v2) = `{"id", "title",
    "description", "project_id", "state_id", "due_at"}`, ni un campo de
    más ni de menos; en v1 (antes del Incremento 5 de este plan), sin
    `due_at`; un campo opcional ausente se devuelve `null`, nunca se
    omite; `due_at` serializado siempre en UTC con `Z`, sin microsegundos.
  - `## Matriz Mínima de Tests`: CRUD feliz de tareas; IDs inexistentes;
    título vacío y espacios ASCII (los invisibles Unicode se piden desde
    ya, por texto explícito de "Normalización de texto", no son una
    regresión futura); proyecto o estado inexistente al crear una tarea;
    filtros solos y combinados; orden estable; esquema exacto; migración
    desde base vacía y **rollback de v2** (implica una migración v2
    separada de la de v1, con su propio `downgrade`); `due_at` omitido,
    válido, sin zona, vencido, futuro y tarea hecha.
- Decisiones de ingeniería relevantes: tests de persistencia contra
  Postgres real; el esquema cambia solo vía Alembic con
  `upgrade`/`downgrade` probados en ambos sentidos; una capacidad nueva
  arranca con un test que falla por su ausencia; no se debilita un test
  existente; nunca se abre `.env`.
- Decisión resuelta con el usuario antes de este plan: crear o actualizar
  una tarea con `project_id` o `state_id` inexistente responde `422` (no
  `404`). `404` queda reservado, en todo el repositorio, para búsquedas
  por id en la URL (`GET/PATCH/DELETE /tasks/{id}`, `/projects/{id}`),
  igual que ya lo usan los endpoints existentes; una referencia inválida
  dentro del cuerpo de la petición se trata como entrada inválida, no
  como un recurso ausente en la URL.

## Fuera de alcance

- Recordatorios, scheduler, zona horaria preferida del usuario y cambio
  automático de estado al vencer una tarea — excluidos explícitamente por
  el propio contrato (`## Tareas v2`).
- Cualquier filtro de `GET /tasks` no mencionado por el contrato (por
  rango de `due_at`, por texto de `title`, etc.): solo `project_id`,
  `state_id` y `overdue`.
- Paginación de `GET /tasks` — el contrato no la pide.
- Endpoints de Estados: ya existen y son un catálogo cerrado; no se
  tocan.
- Normalización Unicode aplicada a campos de Proyecto (`name`,
  `description`) o a `description` de tarea: el contrato la limita
  explícitamente a `title` de tarea.
- Skills, hooks, CI y cualquier cambio de dependencias
  (`pyproject.toml`/`uv.lock`).

## Incrementos

### Incremento 1 — Migración: tabla `tasks` (v1, sin `due_at`)

Nueva migración Alembic, encadenada a `fd59bbd33189`, que crea la tabla
`tasks`: `id` (entero, clave primaria autogenerada), `title`
(`String(200)`, no nulo), `description` (`Text`, nullable), `project_id`
(entero, `ForeignKey("projects.id")`, no nulo) y `state_id` (entero,
`ForeignKey("states.id")`, no nulo). Sin `ON DELETE CASCADE` en ninguna de
las dos FKs (comportamiento por defecto de Postgres, `RESTRICT`): el
contrato exige que "no hay borrado en cascada implícito". Se agregan
índices sobre `project_id` y `state_id` (Postgres no indexa FKs por
defecto y `GET /tasks` filtra por ambos). `downgrade`: `op.drop_table`.

**Comprobación**: test nuevo (amplía `tests/test_migrations.py`) que
valida, contra Postgres real: `upgrade head` crea `tasks` con las columnas
y FKs esperadas; `downgrade` la revierte limpio. `uv run pytest -q
tests/test_migrations.py` en verde.

### Incremento 2 — Cierra el diferimiento: `DELETE /projects/{id}` con `409` real

Ahora que existe la tabla `tasks` con `project_id`, se reemplaza el
borrado simple de `docs/plan-proyectos.md` por la verificación real: antes
de borrar, un `SELECT EXISTS` sobre `tasks WHERE project_id = :id`; si hay
alguna, `409`; si no, `204` (igual que antes). Se actualiza el comentario
en `app/main.py` que documentaba el diferimiento.

**Comprobación**: test nuevo en `tests/test_projects.py` (sin modificar
los existentes) que inserta una fila en `tasks` directamente por SQL
(los endpoints de Tareas todavía no existen en esta secuencia) y verifica
que `DELETE /projects/{id}` de ese proyecto responde `409`. `uv run
pytest -q tests/test_projects.py` en verde.

### Incremento 3 — Alta y listado de tareas v1: `POST /tasks`, `GET /tasks`

Esquema `TaskCreate` en `app/schemas.py` (`title: str`, `description: str
| None = None`, `project_id: int`, `state_id: int`). `POST /tasks` → `201`;
aplica la normalización de `title` (recorte + rechazo `422` si no queda
carácter visible por categoría Unicode); valida existencia de
`project_id` y `state_id` con `SELECT` previo (`422` si no existen, según
la decisión ya resuelta). `GET /tasks` → `200`, admite `project_id` y
`state_id` como filtros solos o combinados, orden por `id` ascendente
(también con filtros aplicados).

**Comprobación**: nuevo `tests/test_tasks.py`, con fixture análoga a
`tests/test_projects.py` (drop + `upgrade head` por test), que cubra: alta
feliz con esquema exacto; título vacío y con solo espacios ASCII →
`422`; título con espacio invisible (`U+200B`) → `422`; `project_id` o
`state_id` inexistente → `422`; lista vacía inicial; filtros solos y
combinados; orden estable por `id` entre llamadas idénticas. `uv run
pytest -q tests/test_tasks.py` y `uv run ruff check .` en verde.

### Incremento 4 — Lectura, actualización y borrado de tareas v1: `GET /tasks/{id}`, `PATCH /tasks/{id}`, `DELETE /tasks/{id}`

Esquema `TaskUpdate` (todos los campos opcionales). `GET /tasks/{id}` →
`200` o `404`. `PATCH /tasks/{id}` → actualización parcial con
`model_dump(exclude_unset=True)` (mismo patrón que `PATCH /projects/{id}`):
si se envía `title`, se normaliza igual que en el alta; si se envían
`project_id`/`state_id`, se validan igual (`422` si no existen). `DELETE
/tasks/{id}` → `204` sin cuerpo, `404` si no existe.

**Comprobación**: casos nuevos en `tests/test_tasks.py`: lectura por id
existente/inexistente; patch de cada campo por separado y combinados;
patch con `project_id`/`state_id` inexistente → `422`; patch sin campos;
patch sobre id inexistente → `404`; borrado existente (`204`) seguido de
`GET` (`404`); borrado de id inexistente → `404`. `uv run pytest -q
tests/test_tasks.py` en verde.

### Incremento 5 — Migración v2: agrega `due_at`

Nueva migración Alembic, encadenada a la del Incremento 1, que agrega la
columna `due_at` (`DateTime(timezone=True)`, nullable) a `tasks`.
`downgrade`: `op.drop_column`.

**Comprobación**: test nuevo en `tests/test_migrations.py` que valida
`upgrade head` agrega la columna con el tipo esperado, y `downgrade`
la revierte limpio (rollback de v2, según la Matriz Mínima). `uv run
pytest -q tests/test_migrations.py` en verde.

### Incremento 6 — Soporte v2 completo: validación, esquema y `overdue`

`TaskCreate`/`TaskUpdate` agregan `due_at: datetime | None = None`, con un
validador que rechaza (`422`) un valor sin `tzinfo`. Antes de guardar, se
normaliza a UTC. Todas las respuestas de tarea (alta, lectura, lista,
patch) devuelven `due_at` siempre presente (`null` si no se fijó),
serializado en UTC con sufijo `Z` y sin microsegundos. `GET
/tasks?overdue=true` filtra tareas con `due_at` anterior al instante de
evaluación (`now()` de la base, evaluado en la propia consulta SQL,
consistente con el resto de consultas del proyecto) y estado con
`code` distinto de `HECHA` (vía join o subconsulta contra `states`);
combinable con `project_id`/`state_id`. Una tarea sin `due_at` nunca
aparece como vencida.

**Comprobación**: casos nuevos en `tests/test_tasks.py`: `due_at` omitido
(queda `null`); `due_at` válido con zona (se normaliza y serializa en
UTC con `Z`, sin microsegundos); `due_at` sin zona → `422`; tarea vencida
aparece en `overdue=true`; tarea con `due_at` futuro no aparece; tarea
vencida pero en estado `HECHA` no aparece; `overdue=true` combinado con
`project_id`/`state_id`. Esquema exacto con `due_at` incluido. `uv run
pytest -q tests/test_tasks.py`, luego `uv run pytest -q` (suite completa)
y `uv run ruff check .` en verde.

## Reglas de ejecución

- Cada incremento queda en un estado confirmable por sí solo.
- No se encadena el siguiente incremento sin aprobación explícita.
- No se modifican `docs/contrato-api.md`, `docs/decisiones-ingenieria.md`,
  `CLAUDE.md`, `.gitignore` ni `.env`. No se abre `.env`.
- No se debilita una comprobación para conseguir verde.
