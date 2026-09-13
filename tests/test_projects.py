"""Tests del recurso Proyectos, conectado a Postgres real.

Corren contra la migración de `projects` (docs/plan-proyectos.md,
Incremento 1) y la conexión compartida de `conftest.py`, según
`docs/decisiones-ingenieria.md`.
"""

import pytest
from httpx import ASGITransport, AsyncClient
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
