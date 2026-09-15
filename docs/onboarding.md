# Onboarding — TaskFlow API

Mapa breve para orientarse en el repositorio. Separa hechos verificados (con
cita de archivo y línea), inferencias razonables y puntos desconocidos.

## 1. Fuente de verdad del comportamiento

- El comportamiento observable de la API (endpoints, códigos de estado,
  esquemas de respuesta, orden de listas, normalización de texto) está fijado
  en `docs/contrato-api.md:1-167`. La línea 3 lo declara explícitamente:
  *"Este documento fija comportamiento observable"*.
- El código en `app/main.py` ya implementa el contrato completo (`states`,
  `projects`, `tasks` con `due_at` y `priority`), no solo `GET /health`.

## 2. Comandos exactos

Todos citados de `README.md`:

| Acción | Comando | Línea |
|---|---|---|
| Instalar dependencias | `uv sync --locked` | `README.md:12` |
| Probar | `uv run pytest -q` | `README.md:18` |
| Revisar estilo | `uv run ruff check .` | `README.md:24` |
| Levantar DB | `docker compose up -d` | `README.md:30` |
| Ejecutar API | `uv run uvicorn app.main:app --reload` | `README.md:36` |
| Detener DB | `docker compose down` | `README.md:45` |

Reglas de estilo activas en `pyproject.toml:26-31`: `line-length = 100`,
`target-version = "py312"`, lint `select = ["E", "F", "I", "UP"]`.

Configuración de tests en `pyproject.toml:33-34`: `asyncio_mode = "auto"`
(pytest-asyncio automático, coherente con el `@pytest.mark.asyncio` de
`tests/test_health.py:7`).

## 3. Motor que deben usar los futuros tests de persistencia

**Desconocido — no hay evidencia en el repo.** Lo que sí está fijado:

- El motor de base de datos es PostgreSQL 18 (`compose.yaml:3`, imagen
  `postgres:18-alpine`).
- El contrato exige que el catálogo de estados se cargue por **migración**,
  no por script de init de Docker (`docs/contrato-api.md:70-77`), y que sea
  idempotente (`docs/contrato-api.md:79-80`).
- Pero no hay ningún driver, ORM ni herramienta de migración declarados:
  `pyproject.toml:6-17` no lista `sqlalchemy`, `asyncpg`, `psycopg` ni
  `alembic` en dependencias ni en el grupo `dev`. Tampoco aparecen en
  `app/main.py` ni en ningún otro archivo del repo (búsqueda `grep` sin
  resultados fuera del propio texto del contrato).
- `docs/contrato-api.md:79` enlaza a `../docs/glosario.md#idempotente`, pero
  ese archivo **no existe** en el repo (`git ls-files` no lo lista, y no hay
  commits que lo hayan tocado).

## 4. Límites sobre archivos con secretos

- `.gitignore:1` ignora `.env` — el archivo real de secretos nunca debe
  commitearse.
- `.env.example:1-6` es la plantilla versionada, con credenciales
  explícitamente ficticias para desarrollo local (línea 2: *"Estos son
  valores ficticios pensados solo para desarrollo local"*).
- `compose.yaml:5-7` usa esos mismos valores como default (`taskflow` /
  `taskflow_dev_password` / `taskflow`) si no existe `.env`, permitiendo
  levantar la DB sin crear el archivo (`README.md:50-51`).
- Existe un `.env` real en el directorio de trabajo, pero correctamente
  ignorado por git — no está trackeado, no se filtra.

## 5. Decisiones que no se pueden establecer con evidencia

- **Motor/driver de persistencia en Python** (SQLAlchemy, asyncpg, psycopg,
  etc.) y herramienta de migraciones (Alembic u otra): no declarados en
  ningún archivo.
- **Estructura interna de la app** más allá de `app/main.py`: el contrato
  dice explícitamente que "la estructura interna queda abierta"
  (`docs/contrato-api.md:3`), así que routers, capa de modelos, capa de
  servicios, etc. son decisiones futuras, no del repo actual.
- `docs/glosario.md`: referenciado pero inexistente; no se puede confirmar su
  contenido previsto.
- Sesiones futuras mencionadas en el contrato ("la sesión 7", "la sesión 10"
  — `docs/contrato-api.md:30`, `:12`) no tienen artefactos en el repo; solo
  son referencias textuales sin plan asociado visible.
