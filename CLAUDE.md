# CLAUDE.md

Guía para Claude Code en este repositorio. TaskFlow API (FastAPI + PostgreSQL).

## Fuentes de verdad

- `docs/contrato-api.md` fija el comportamiento observable (endpoints,
  códigos de estado, esquemas, orden de listas, normalización de texto).
  Ningún cambio de código lo contradice; se edita primero el documento,
  y solo cuando el ticket pide explícitamente cambiar el contrato.
- `docs/decisiones-ingenieria.md` fija decisiones de ingeniería del equipo
  no deducibles del código (base de datos, migraciones, pruebas, datos
  locales). Consultarlo antes de tocar esas áreas.

## Comandos canónicos

```bash
uv sync --locked      # instalar dependencias
uv run pytest -q      # correr tests
uv run ruff check .   # lint
```

## Reglas no negociables

- Las pruebas que ejercitan persistencia corren contra **PostgreSQL**.
  Nunca SQLite: no reproduce las mismas restricciones, tipos ni migraciones
  (detalle en `docs/decisiones-ingenieria.md`).
- Nunca abrir, mostrar, editar ni confirmar (`git add`/commit) `.env`. Para
  nombres de variables, usar `.env.example`.
- Nunca debilitar ni eliminar un test existente para conseguir verde. Si el
  comportamiento acordado cambió, primero se actualiza el contrato y después
  el test, en un commit separado.
