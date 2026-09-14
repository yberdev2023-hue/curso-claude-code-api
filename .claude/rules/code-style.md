# Convenciones de estilo de código

## Tipado

- Toda función declara su tipo de retorno explícito, incluida `-> None`.
- Los tipos opcionales se escriben `X | None`, nunca `Optional[X]`.
- Las uniones se escriben `X | Y`, nunca `Union[X, Y]`.
- `Sequence` y equivalentes se importan de `collections.abc`, nunca de `typing`.
- Las colecciones genéricas usan el tipo integrado (`dict[str, object]`, `list[dict[str, object]]`), nunca `typing.Dict`/`typing.List`.
- Las fechas con zona horaria usan el alias `datetime.UTC`, nunca `datetime.timezone.utc`.
- Un parámetro sin una anotación razonable (por ejemplo, una fila de resultado de SQLAlchemy) se deja sin anotar antes que forzar un tipo impreciso.

## Esquemas frente a diccionarios sueltos

- El cuerpo de una petición (`POST`/`PATCH`) siempre se recibe como una clase de Pydantic (`BaseModel`), nunca como un `dict` sin tipar.
- Una validación de campo (formato, rango, normalización) vive en un `@field_validator` del esquema, nunca como un `if` suelto dentro del endpoint.
- La lógica de validación que comparten dos esquemas (por ejemplo, alta y actualización) se extrae a una función de módulo aparte, y cada `@field_validator` es un wrapper de una línea que la llama.
- La respuesta de un endpoint se arma a mano como `dict`, nunca con un `response_model` de Pydantic, porque no hay una capa ORM declarativa que lo justifique.
- Cada recurso tiene una única función `_<recurso>_row_to_dict(row)` que arma su diccionario de salida; ningún endpoint construye ese diccionario inline por su cuenta.
- Una actualización parcial (`PATCH`) se calcula con `payload.model_dump(exclude_unset=True)`, nunca comparando campo por campo contra `None`.

## Funciones async

- Un endpoint es `async def` si toca la base de datos; si no toca la base (como `/health`), es `def` a secas.
- Una lectura usa `async with get_engine().connect() as conn:`; una escritura usa `async with get_engine().begin() as conn:` — nunca se llama `.commit()` o `.rollback()` a mano dentro de un endpoint.
- El `return` de un endpoint queda siempre fuera del bloque `async with`, después de que la conexión se cerró.
- Toda consulta SQL se escribe con `sqlalchemy.text()` y parámetros nombrados (`:campo`), nunca interpolando un valor directamente en la cadena.
- Un nombre de columna se arma dinámicamente en un `SET`/`WHERE` (por ejemplo, en un `PATCH` parcial) solo a partir de las claves ya validadas por el propio esquema de Pydantic, nunca a partir de una clave arbitraria del cliente, y ese hecho se deja dicho en un comentario junto al `f-string`.
- Un `SELECT` siempre lista las columnas que necesita por nombre; no se usa `SELECT *`.

## Manejo de errores

- Un error de negocio hacia el cliente se señala con `fastapi.HTTPException(status_code=..., detail="<mensaje>")`, nunca dejando propagar una excepción sin capturar.
- Un `HTTPException` siempre lleva `detail` con un mensaje legible; nunca se lanza sin él.
- Una validación de esquema (formato, rango, normalización) señala su rechazo con un `raise ValueError(...)` dentro del `@field_validator`, y es FastAPI quien la convierte en `422` — nunca se lanza un `HTTPException` a mano por un error de este tipo.
- Una comprobación de existencia contra la base (por ejemplo, que un `project_id` referenciado exista) se hace con una función `async def _validar_<algo>_existe(conn, ...)` dedicada, reutilizada desde alta y desde `PATCH`, nunca duplicada inline en cada endpoint.
- El código de estado de una ruta que no es el default (`201`, `204`) se declara con la constante de `fastapi.status` (`status.HTTP_201_CREATED`); el código de estado de un `HTTPException` se escribe como entero literal (`404`, `409`, `422`).

## Lo que `ruff` ya exige

- Línea máxima de 100 caracteres (`line-length = 100`).
- Sintaxis moderna de Python 3.12 (`target-version = "py312"`): sin `Union`/`Optional`, sin imports de `typing` para lo que ya cubre `collections.abc` o los tipos integrados.
- Imports ordenados y agrupados (regla `I`, estilo isort): librería estándar, terceros, y del propio proyecto, en ese orden.
- Cero imports sin usar (regla `F`): un import que ya no hace falta se borra, no se comenta.
- Cero errores de estilo `pycodestyle` (regla `E`): esto ya lo aplica `ruff check .`, no hace falta revisarlo a mano.
