# Plan: conexión de TaskFlow a PostgreSQL

Este documento registra la secuencia de incrementos acordada para conectar la
API a PostgreSQL. Cada incremento es confirmable por sí solo; no se encadena
el siguiente sin aprobación explícita.

Fuentes: `docs/contrato-api.md` (secciones Salud y Estados),
`docs/decisiones-ingenieria.md`, `CLAUDE.md`.

Fuera de alcance: proyectos, tareas, filtros, `due_at`, skills, hooks y CI.

## Estado de partida

- Código: solo `GET /health` implementado (`app/main.py`), sin ORM, driver ni
  Alembic declarados en `pyproject.toml`.
- Infraestructura: `compose.yaml` levanta Postgres 18 con valores de
  desarrollo por defecto; `.env.example` documenta las variables
  (`POSTGRES_USER/PASSWORD/DB/PORT`).
- Tests: solo `tests/test_health.py`, sin fixtures ni configuración de base
  de datos.
- Contrato relevante:
  - `GET /health` → `200 {"status": "ok"}`, sin credenciales ni detalles
    internos.
  - `GET /states` → `200` con catálogo fijo `PENDIENTE, EN_CURSO, BLOQUEADA,
    HECHA`, ordenado por campo de orden del catálogo y `id` como desempate.
  - El catálogo de estados se carga por **migración** (no por script de
    Docker), y debe ser **idempotente**.
  - Los estados no tienen otros endpoints (no se crean ni se borran vía
    API).
- Decisiones de ingeniería relevantes: los tests de persistencia corren
  contra Postgres real (nunca SQLite); el esquema cambia solo vía Alembic,
  con `upgrade`/`downgrade` probados en ambos sentidos; una capacidad nueva
  arranca con un test que falla por su ausencia; nunca se abre `.env`.

## Incrementos

### Incremento 1 — Dependencias de persistencia

Agregar a `pyproject.toml` (grupo principal y/o dev): SQLAlchemy (async),
`asyncpg` como driver, y Alembic. Correr `uv sync --locked` para regenerar el
lockfile.

**Comprobación**: `uv sync --locked` termina sin error; `uv run ruff check .`
sigue en verde. Sin cambios de comportamiento todavía, así que no hay test
nuevo.

### Incremento 2 — Configuración de conexión a la base

Módulo de settings que lea la URL de conexión desde variables de entorno
(nombres tomados de `.env.example`, sin abrir `.env`), y arranque de Alembic
con `alembic init` apuntando a esa configuración, sin migraciones todavía.
`alembic init` encaja con el estado de partida porque el repositorio no
tiene ninguna estructura de Alembic todavía (sin carpeta `alembic/` ni
`alembic.ini`), así que corresponde la inicialización estándar y no una
migración manual de un arranque existente.

**Comprobación**: `uv run alembic current` corre sin error contra la base
levantada con `docker compose up -d`. `uv run alembic current` encaja con
el resto del plan porque ya usa el prefijo `uv run` de los comandos
canónicos del repositorio (`CLAUDE.md`) y es el comando de Alembic que
verifica el estado de la base sin aplicar cambios, coherente con que este
incremento no crea migraciones todavía.

### Incremento 3 — Migración inicial: tabla de estados + seed idempotente

Migración Alembic que crea la tabla de estados y siembra el catálogo fijo
(`PENDIENTE, EN_CURSO, BLOQUEADA, HECHA`) de forma idempotente, con
`downgrade` simétrico.

**Comprobación**: test nuevo contra Postgres real que valida: base vacía →
`upgrade head` → catálogo presente; migrar dos veces no duplica; `downgrade`
revierte limpio. Regla del equipo: primero el test que falla por ausencia de
la migración, luego la migración que lo pone en verde.

### Incremento 4 — Fixture de tests con Postgres real + `conftest.py`

Fixture async de sesión/conexión a la base para que los tests de
persistencia (incluidos los del incremento 3) corran contra Postgres, no
contra mocks ni SQLite, alineado con `docs/decisiones-ingenieria.md`.

**Comprobación**: `uv run pytest -q` verde, incluyendo el test de migración
del incremento 3, corriendo contra la instancia de `compose.yaml`.

### Incremento 5 — `GET /states` conectado a la base

Implementar el endpoint leyendo el catálogo real desde Postgres, con el
orden exacto que exige el contrato (campo de orden, `id` como desempate) y
el esquema de respuesta exacto (`{"id", "code"}`, sin campos de más).

**Comprobación**: test nuevo de `GET /states` contra Postgres real que
verifica status, orden estable entre llamadas y forma exacta del esquema.
`uv run pytest -q` y `uv run ruff check .` en verde.

## Reglas de ejecución

- Cada incremento queda en un estado confirmable por sí solo.
- No se encadena el siguiente incremento sin aprobación explícita.
- No se modifican `docs/contrato-api.md`, `docs/decisiones-ingenieria.md`,
  `CLAUDE.md`, `.gitignore` ni `.env`. No se abre `.env`.
- No se debilita una comprobación para conseguir verde.
