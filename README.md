# TaskFlow API

API de TaskFlow construida con FastAPI, administrada con `uv` sobre Python 3.12,
persistida en PostgreSQL. El comportamiento observable completo (endpoints,
códigos de estado, esquemas de respuesta) está fijado en
[`docs/contrato-api.md`](docs/contrato-api.md).

## Recorrido

1. Instalar las dependencias fijadas en el lockfile:

   ```bash
   uv sync --locked
   ```

2. Levantar la base de datos PostgreSQL:

   ```bash
   docker compose up -d
   ```

3. Aplicar las migraciones hasta la cabeza actual:

   ```bash
   uv run alembic upgrade head
   ```

4. Ejecutar la API en modo desarrollo:

   ```bash
   uv run uvicorn app.main:app --reload
   ```

   La aplicación queda disponible en `http://127.0.0.1:8000`, con
   `GET /health` respondiendo `{"status": "ok"}`.

5. Probar la API con las peticiones de ejemplo de
   [`api.http`](api.http) (requiere la extensión REST Client de VS Code, o
   un cliente equivalente que entienda bloques `###`): abrí el archivo y
   ejecutá la primera petición (`GET /health`); las siguientes se apoyan en
   los ids que devuelven las anteriores.

   Sin esa extensión, se puede reproducir cada petición a mano con `curl`,
   leyendo método y ruta del bloque (por ejemplo, la primera equivale a
   `curl http://127.0.0.1:8000/health`); las peticiones que dependen de un
   id devuelto por otra (`{{crearProyecto.response.body.$.id}}`, etc.) piden
   copiar ese id a mano de la respuesta anterior.

6. Ejecutar la suite de tests (requiere la base del paso 2 levantada; la
   suite migra y revierte su propio esquema en cada test):

   ```bash
   uv run pytest -q
   ```

   La suite deja la base sin ninguna migración aplicada al terminar. Antes
   de volver a usar la API a mano, repetí el paso 3.

7. Revisar el estilo y la calidad del código:

   ```bash
   uv run ruff check .
   ```

8. Al terminar, apagar la base de datos:

   ```bash
   docker compose down
   ```

## Configuración

`compose.yaml` funciona con valores locales por defecto sin necesidad de crear
un archivo `.env`. Para personalizarlos, copia `.env.example` a `.env` y
ajusta `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` y `POSTGRES_PORT`.
