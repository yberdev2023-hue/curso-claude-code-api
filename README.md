# TaskFlow API

API de TaskFlow construida con FastAPI, administrada con `uv` sobre Python 3.12.
Esta primera entrega expone únicamente `GET /health`; el resto del contrato
(`docs/contrato-api.md`) se implementa en sesiones posteriores.

## Recorrido

1. Instalar las dependencias fijadas en el lockfile:

   ```bash
   uv sync --locked
   ```

2. Ejecutar la suite de tests:

   ```bash
   uv run pytest -q
   ```

3. Revisar el estilo y la calidad del código:

   ```bash
   uv run ruff check .
   ```

4. Levantar la base de datos PostgreSQL:

   ```bash
   docker compose up -d
   ```

5. Ejecutar la API en modo desarrollo:

   ```bash
   uv run uvicorn app.main:app --reload
   ```

   La aplicación queda disponible en `http://127.0.0.1:8000`, con
   `GET /health` respondiendo `{"status": "ok"}`.

6. Al terminar, apagar la base de datos:

   ```bash
   docker compose down
   ```

## Configuración

`compose.yaml` funciona con valores locales por defecto sin necesidad de crear
un archivo `.env`. Para personalizarlos, copia `.env.example` a `.env` y
ajusta `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` y `POSTGRES_PORT`.
