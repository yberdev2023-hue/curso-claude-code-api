# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Comandos

Gestión de dependencias con `uv` sobre Python 3.12 (`requires-python = "==3.12.*"`):

```bash
uv sync --locked              # instalar dependencias fijadas en el lockfile
uv run pytest -q              # ejecutar toda la suite de tests
uv run pytest -q tests/test_health.py::test_health_status_and_body  # un solo test
uv run ruff check .           # lint (E, F, I, UP; line-length 100)
docker compose up -d          # levantar PostgreSQL (usa defaults si no existe .env)
docker compose down           # apagar PostgreSQL
uv run uvicorn app.main:app --reload  # correr la API en http://127.0.0.1:8000
```

No crear `.env` es válido: `compose.yaml` trae defaults de desarrollo. Para
personalizar, copiar `.env.example` a `.env`.

## Arquitectura

Este proyecto es la API de **TaskFlow** (FastAPI + PostgreSQL), desarrollada
de forma incremental a través de un curso. Dos documentos gobiernan todo el
trabajo, y son más importantes que el estado actual del código:

- **`docs/contrato-api.md`** es la fuente de verdad del comportamiento
  observable: endpoints, códigos de estado, esquemas de respuesta exactos,
  orden determinista de listas, normalización de texto y convenciones de
  error. Dice explícitamente que "la estructura interna queda abierta" — solo
  el comportamiento externo es contrato. Cualquier cambio de código debe
  cumplir este documento, no al revés; no modificar las tablas del contrato
  sin editar primero el documento.
- **`README.md`** describe el estado real de avance. El código hoy solo
  implementa `GET /health` (`app/main.py`); el resto del contrato (estados,
  proyectos, tareas, `due_at`) está especificado pero pendiente de
  implementación en sesiones posteriores del curso.

Puntos del contrato con más probabilidad de generar bugs sutiles si se
implementan sin releerlos:

- **Normalización de `title`**: recortar espacios y luego rechazar con `422`
  si no queda ningún carácter visible — un `strip()` común no basta, hay que
  rechazar por categoría Unicode (`Cc`, `Cf`, `Zl`, `Zp`, `Zs`), no solo
  espacios ASCII.
- **`due_at`**: opcional; sin zona horaria se rechaza con `422` (no se asume
  ninguna); se serializa siempre en UTC con sufijo `Z` y sin microsegundos
  (`2026-03-01T09:00:00Z`), nunca con offset `+00:00`.
- **Esquemas de respuesta exactos**: un campo opcional ausente se serializa
  como `null`, nunca se omite; no debe haber campos de más ni de menos que los
  documentados; las colecciones se devuelven como lista JSON en la raíz, sin
  objeto envolvente.
- **Orden estable**: `GET /states` por campo de orden del catálogo con `id`
  como desempate; `GET /projects` y `GET /tasks` por `id` ascendente (también
  con filtros aplicados).
- **Catálogo de estados** (`PENDIENTE`, `EN_CURSO`, `BLOQUEADA`, `HECHA`): no
  tiene endpoints de escritura, y el contrato exige que se cargue por
  **migración** (no por script de init de Docker), de forma idempotente —
  así funciona igual en un volumen ya existente que en uno nuevo.
- **Borrado de proyecto con tareas**: `409`, sin cascada implícita.
- Errores con forma estable `{"detail": "<mensaje>"}`.

No hay todavía ORM, driver de PostgreSQL ni herramienta de migraciones
declarados en `pyproject.toml`; esa decisión (SQLAlchemy/asyncpg/psycopg,
Alembic u otra) queda para cuando se implemente persistencia, y debe
satisfacer el requisito de migraciones idempotentes del contrato.

`.env` real está en el repo pero ignorado por git; `.env.example` es la
plantilla versionada con credenciales ficticias de desarrollo.
