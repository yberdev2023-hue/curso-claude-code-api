"""Tests del recurso Tareas v1, conectado a Postgres real.

Corren contra la migración de `tasks` (docs/plan-tareas.md, Incremento 1)
y la conexión compartida de `conftest.py`, según
`docs/decisiones-ingenieria.md`. No cubren `due_at` (v2): eso queda para
los incrementos 5 y 6 del plan, fuera de este archivo por ahora.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db import dispose_engine
from app.main import app
from tests.conftest import reset_schema, run_alembic


@pytest.fixture(autouse=True)
async def tareas_migradas(db_connection: AsyncConnection):
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


async def obtener_id_estado(db_connection: AsyncConnection, code: str) -> int:
    return (
        await db_connection.execute(
            text("SELECT id FROM states WHERE code = :code"), {"code": code}
        )
    ).scalar_one()


async def crear_tarea(client: AsyncClient, **kwargs: object) -> dict:
    response = await client.post("/tasks", json=kwargs)
    assert response.status_code == 201, response.text
    return response.json()


# --- Incremento 3: alta y listado -----------------------------------------


@pytest.mark.asyncio
async def test_post_tasks_devuelve_201_y_esquema_exacto(db_connection: AsyncConnection) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        estado = await obtener_id_estado(db_connection, "PENDIENTE")

        response = await client.post(
            "/tasks",
            json={
                "title": "Regar las plantas",
                "description": "Todos los días",
                "project_id": proyecto["id"],
                "state_id": estado,
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert set(body.keys()) == {"id", "title", "description", "project_id", "state_id"}
    assert isinstance(body["id"], int) and body["id"] > 0
    assert body["title"] == "Regar las plantas"
    assert body["description"] == "Todos los días"
    assert body["project_id"] == proyecto["id"]
    assert body["state_id"] == estado


@pytest.mark.asyncio
async def test_post_tasks_sin_description_la_devuelve_null(db_connection: AsyncConnection) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        estado = await obtener_id_estado(db_connection, "PENDIENTE")

        response = await client.post(
            "/tasks",
            json={"title": "Regar", "project_id": proyecto["id"], "state_id": estado},
        )

    assert response.status_code == 201
    body = response.json()
    assert "description" in body
    assert body["description"] is None


@pytest.mark.asyncio
async def test_post_tasks_titulo_vacio_devuelve_422(db_connection: AsyncConnection) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        estado = await obtener_id_estado(db_connection, "PENDIENTE")

        response = await client.post(
            "/tasks",
            json={"title": "", "project_id": proyecto["id"], "state_id": estado},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_tasks_titulo_solo_espacios_ascii_devuelve_422(
    db_connection: AsyncConnection,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        estado = await obtener_id_estado(db_connection, "PENDIENTE")

        response = await client.post(
            "/tasks",
            json={"title": "   ", "project_id": proyecto["id"], "state_id": estado},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_tasks_titulo_con_invisible_unicode_devuelve_422(
    db_connection: AsyncConnection,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        estado = await obtener_id_estado(db_connection, "PENDIENTE")

        response = await client.post(
            "/tasks",
            json={"title": "​", "project_id": proyecto["id"], "state_id": estado},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_tasks_proyecto_inexistente_devuelve_422(db_connection: AsyncConnection) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        estado = await obtener_id_estado(db_connection, "PENDIENTE")

        response = await client.post(
            "/tasks",
            json={"title": "Regar", "project_id": 999999, "state_id": estado},
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "El proyecto 999999 no existe"}


@pytest.mark.asyncio
async def test_post_tasks_estado_inexistente_devuelve_422() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")

        response = await client.post(
            "/tasks",
            json={"title": "Regar", "project_id": proyecto["id"], "state_id": 999999},
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "El estado 999999 no existe"}


@pytest.mark.asyncio
async def test_get_tasks_lista_vacia() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/tasks")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_tasks_orden_por_id_ascendente_y_estable(db_connection: AsyncConnection) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        estado = await obtener_id_estado(db_connection, "PENDIENTE")

        creadas = [
            await crear_tarea(client, title="A", project_id=proyecto["id"], state_id=estado),
            await crear_tarea(client, title="B", project_id=proyecto["id"], state_id=estado),
            await crear_tarea(client, title="C", project_id=proyecto["id"], state_id=estado),
        ]
        ids_esperados = [t["id"] for t in creadas]

        primera = (await client.get("/tasks")).json()
        segunda = (await client.get("/tasks")).json()

    assert [t["id"] for t in primera] == sorted(ids_esperados)
    assert primera == segunda


@pytest.mark.asyncio
async def test_get_tasks_filtra_por_project_id_y_state_id_solos_y_combinados(
    db_connection: AsyncConnection,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto_a = await crear_proyecto(client, name="Casa")
        proyecto_b = await crear_proyecto(client, name="Trabajo")
        pendiente = await obtener_id_estado(db_connection, "PENDIENTE")
        en_curso = await obtener_id_estado(db_connection, "EN_CURSO")

        tarea_a_pendiente = await crear_tarea(
            client, title="A-pendiente", project_id=proyecto_a["id"], state_id=pendiente
        )
        await crear_tarea(
            client, title="A-en_curso", project_id=proyecto_a["id"], state_id=en_curso
        )
        await crear_tarea(
            client, title="B-pendiente", project_id=proyecto_b["id"], state_id=pendiente
        )

        solo_proyecto = (
            await client.get("/tasks", params={"project_id": proyecto_a["id"]})
        ).json()
        solo_estado = (await client.get("/tasks", params={"state_id": pendiente})).json()
        combinado = (
            await client.get(
                "/tasks",
                params={"project_id": proyecto_a["id"], "state_id": pendiente},
            )
        ).json()

    assert len(solo_proyecto) == 2
    assert len(solo_estado) == 2
    assert combinado == [tarea_a_pendiente]
