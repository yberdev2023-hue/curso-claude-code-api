"""Tests del recurso Proyectos, conectado a Postgres real.

Corren contra la migración de `projects` (docs/plan-proyectos.md,
Incremento 1) y la conexión compartida de `conftest.py`, según
`docs/decisiones-ingenieria.md`.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db import dispose_engine
from app.main import app
from tests.conftest import reset_schema, run_alembic


@pytest.fixture(autouse=True)
async def proyectos_migrados(db_connection: AsyncConnection):
    # El engine de la app queda atado al event loop del test anterior; se
    # descarta antes de cada test para que la próxima consulta cree uno
    # nuevo en el loop actual (mismo motivo que en tests/conftest.py).
    await dispose_engine()

    await reset_schema(db_connection)

    assert run_alembic("upgrade", "head").returncode == 0

    yield

    await reset_schema(db_connection)
    await dispose_engine()


async def crear_proyecto(client: AsyncClient, **kwargs: object) -> dict:
    response = await client.post("/projects", json=kwargs)
    assert response.status_code == 201, response.text
    return response.json()


# --- Incremento 2: alta y lectura ---------------------------------------


@pytest.mark.asyncio
async def test_post_projects_devuelve_201_y_esquema_exacto() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/projects", json={"name": "Casa", "description": "Tareas del hogar"}
        )

    assert response.status_code == 201
    body = response.json()
    assert set(body.keys()) == {"id", "name", "description"}
    assert isinstance(body["id"], int) and body["id"] > 0
    assert body["name"] == "Casa"
    assert body["description"] == "Tareas del hogar"


@pytest.mark.asyncio
async def test_post_projects_sin_description_la_devuelve_null() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/projects", json={"name": "Casa"})

    assert response.status_code == 201
    body = response.json()
    assert "description" in body
    assert body["description"] is None


@pytest.mark.asyncio
async def test_post_projects_sin_name_devuelve_422() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/projects", json={"description": "sin nombre"})

    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_get_projects_lista_vacia() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/projects")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_projects_orden_por_id_ascendente_y_estable_entre_llamadas() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        creados = [
            await crear_proyecto(client, name="Casa"),
            await crear_proyecto(client, name="Trabajo"),
            await crear_proyecto(client, name="Estudio"),
        ]
        ids_esperados = [p["id"] for p in creados]

        primera = (await client.get("/projects")).json()
        segunda = (await client.get("/projects")).json()

    assert [p["id"] for p in primera] == sorted(ids_esperados)
    assert primera == segunda


@pytest.mark.asyncio
async def test_get_project_by_id_existente() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        creado = await crear_proyecto(client, name="Casa", description="Tareas del hogar")

        response = await client.get(f"/projects/{creado['id']}")

    assert response.status_code == 200
    assert response.json() == creado


@pytest.mark.asyncio
async def test_get_project_by_id_inexistente_devuelve_404() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/projects/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Proyecto no encontrado"}


# --- Incremento 3: PATCH -------------------------------------------------


@pytest.mark.asyncio
async def test_patch_project_solo_name() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        creado = await crear_proyecto(client, name="Casa", description="Tareas del hogar")

        response = await client.patch(f"/projects/{creado['id']}", json={"name": "Hogar"})

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Hogar"
    assert body["description"] == "Tareas del hogar"


@pytest.mark.asyncio
async def test_patch_project_solo_description() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        creado = await crear_proyecto(client, name="Casa", description="Tareas del hogar")

        response = await client.patch(
            f"/projects/{creado['id']}", json={"description": "Actualizada"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Casa"
    assert body["description"] == "Actualizada"


@pytest.mark.asyncio
async def test_patch_project_name_y_description_a_la_vez() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        creado = await crear_proyecto(client, name="Casa", description="Tareas del hogar")

        response = await client.patch(
            f"/projects/{creado['id']}",
            json={"name": "Hogar", "description": "Actualizada"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Hogar"
    assert body["description"] == "Actualizada"


@pytest.mark.asyncio
async def test_patch_project_sin_campos_no_cambia_nada() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        creado = await crear_proyecto(client, name="Casa", description="Tareas del hogar")

        response = await client.patch(f"/projects/{creado['id']}", json={})

    assert response.status_code == 200
    assert response.json() == creado


@pytest.mark.asyncio
async def test_patch_project_inexistente_devuelve_404() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch("/projects/999999", json={"name": "Nuevo"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Proyecto no encontrado"}


# --- Incremento 4: DELETE -------------------------------------------------


@pytest.mark.asyncio
async def test_delete_project_existente_devuelve_204_sin_cuerpo() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        creado = await crear_proyecto(client, name="Casa")

        response = await client.delete(f"/projects/{creado['id']}")

    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.asyncio
async def test_delete_project_luego_get_devuelve_404() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        creado = await crear_proyecto(client, name="Casa")

        await client.delete(f"/projects/{creado['id']}")
        response = await client.get(f"/projects/{creado['id']}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_project_inexistente_devuelve_404() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete("/projects/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Proyecto no encontrado"}


# --- Cierre de docs/plan-proyectos.md: 409 real (docs/plan-tareas.md, Incremento 2) ---


@pytest.mark.asyncio
async def test_delete_project_con_tareas_devuelve_409(db_connection: AsyncConnection) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        creado = await crear_proyecto(client, name="Casa")

        # Los endpoints de Tareas todavía no existen en esta secuencia
        # (docs/plan-tareas.md, Incremento 2 corre antes que el 3), así
        # que la fila se inserta directo por SQL.
        estado = (
            await db_connection.execute(text("SELECT id FROM states WHERE code = 'PENDIENTE'"))
        ).scalar_one()
        await db_connection.execute(
            text(
                "INSERT INTO tasks (title, project_id, state_id) "
                "VALUES ('Regar las plantas', :project_id, :state_id)"
            ),
            {"project_id": creado["id"], "state_id": estado},
        )
        await db_connection.commit()

        response = await client.delete(f"/projects/{creado['id']}")

    assert response.status_code == 409
    assert response.json() == {"detail": "El proyecto tiene tareas asociadas"}


@pytest.mark.asyncio
async def test_delete_project_con_tarea_creada_via_api_devuelve_409() -> None:
    # Igual que test_delete_project_con_tareas_devuelve_409, pero de punta a
    # punta por la API real (POST /tasks ya existe: docs/plan-tareas.md,
    # Incremento 3), sin insertar la fila por SQL.
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")

        estados = (await client.get("/states")).json()
        pendiente = next(e["id"] for e in estados if e["code"] == "PENDIENTE")

        tarea = await client.post(
            "/tasks",
            json={
                "title": "Regar las plantas",
                "project_id": proyecto["id"],
                "state_id": pendiente,
            },
        )
        assert tarea.status_code == 201, tarea.text

        response = await client.delete(f"/projects/{proyecto['id']}")

    assert response.status_code == 409
    assert response.json() == {"detail": "El proyecto tiene tareas asociadas"}
