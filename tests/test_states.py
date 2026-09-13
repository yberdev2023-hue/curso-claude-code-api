"""Tests de GET /states, conectado a Postgres real.

Corren contra la migración inicial (Incremento 3) y la conexión compartida
de `conftest.py` (Incremento 4), según `docs/decisiones-ingenieria.md`.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db import dispose_engine
from app.main import app
from tests.conftest import reset_schema, run_alembic

CATALOGO_ESPERADO = ["PENDIENTE", "EN_CURSO", "BLOQUEADA", "HECHA"]


@pytest.fixture(autouse=True)
async def catalogo_migrado(db_connection: AsyncConnection):
    # El engine de la app queda atado al event loop del test anterior; se
    # descarta antes de cada test para que la próxima consulta cree uno
    # nuevo en el loop actual (mismo motivo que en tests/conftest.py).
    await dispose_engine()

    await reset_schema(db_connection)

    assert run_alembic("upgrade", "head").returncode == 0

    yield

    await reset_schema(db_connection)
    await dispose_engine()


@pytest.mark.asyncio
async def test_states_status_orden_y_esquema_exacto() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/states")

    assert response.status_code == 200

    body = response.json()
    assert [item["code"] for item in body] == CATALOGO_ESPERADO
    for item in body:
        assert set(item.keys()) == {"id", "code"}


@pytest.mark.asyncio
async def test_states_orden_estable_entre_llamadas() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        primera = (await client.get("/states")).json()
        segunda = (await client.get("/states")).json()

    assert primera == segunda
