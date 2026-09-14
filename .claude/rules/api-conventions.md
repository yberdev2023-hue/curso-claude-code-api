# Convenciones de la API

## Esquema de respuesta exacto

- El contrato de cada esquema de respuesta está fijado en `docs/contrato-api.md`, sección "Esquemas de Respuesta": los campos declarados ahí, ni uno más ni uno menos.
- La forma real de la respuesta la decide la función `_<recurso>_row_to_dict(row)` de `app/main.py`, no el esquema de entrada de `app/schemas.py`: agregar o quitar un campo de esa función es lo que cambia el esquema de salida.
- Un campo opcional ausente se devuelve como `null` en el `dict` construido en `app/main.py`; nunca se omite la clave.

## Código de estado por tipo de error

- `404` es para un recurso buscado por id en la ruta (`GET`/`PATCH`/`DELETE /projects/{project_id}`, `GET`/`PATCH`/`DELETE /tasks/{task_id}` en `app/main.py`), cuando ese id no existe.
- `409` es para un conflicto de estado, no de entrada: hoy el único caso es `DELETE /projects/{project_id}` cuando el proyecto tiene tareas asociadas, implementado en `app/main.py`.
- `422` es para entrada inválida, con dos mecanismos según dónde se detecta: un `raise ValueError(...)` dentro de un `@field_validator` de `app/schemas.py` (título vacío, `due_at` sin zona, `priority` fuera de rango), o un `HTTPException(status_code=422, ...)` manual en `app/main.py` cuando la invalidez depende de una consulta a la base (`project_id`/`state_id` referenciados que no existen).

## Colecciones: lista en la raíz y orden estable

- `GET /states`, `GET /projects` y `GET /tasks` en `app/main.py` devuelven siempre `list[dict[str, object]]` como raíz del JSON; nunca un objeto envolvente con metadatos.
- El orden de cada colección es estable entre llamadas idénticas, fijado en `docs/contrato-api.md` (sección "Convenciones", tabla "Orden de las listas"): `id` ascendente para proyectos y tareas, campo de orden del catálogo más `id` como desempate para estados.
- El orden lo da la propia consulta SQL (`ORDER BY ...`) en `app/main.py`, nunca un ordenamiento posterior en Python sobre la lista ya traída.

## Un campo nuevo se agrega en tres capas

- **Migración**: un archivo nuevo en `alembic/versions/`, encadenado a la cabeza real (`uv run alembic heads`), que agrega la columna a la tabla correspondiente.
- **Esquema**: el campo declarado en la clase de Pydantic correspondiente de `app/schemas.py` (alta y actualización), con su `@field_validator` si necesita normalización o rango.
- **Validación en el endpoint**: la columna sumada a los `SELECT`/`INSERT`/`UPDATE` del endpoint en `app/main.py`, y al `dict` de salida de su función `_<recurso>_row_to_dict`.
- Ninguna de las tres capas se toca antes de que el campo exista en `docs/contrato-api.md`: el contrato se actualiza primero, en su propio commit, y recién después las tres capas de código.
