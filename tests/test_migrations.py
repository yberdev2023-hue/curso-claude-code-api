"""Tests de las migraciones: catálogo de estados y tabla de proyectos.

Corren contra Postgres real (la instancia de `compose.yaml`), nunca contra
SQLite ni mocks, según `docs/decisiones-ingenieria.md`, usando la conexión y
los helpers compartidos de `conftest.py`. Manejan Alembic vía subprocess
para poder validar el ciclo completo upgrade/downgrade tal como lo ve un
usuario del CLI, y limpian el esquema de las tablas gestionadas antes y
después de cada prueba para partir de una base vacía.
"""

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from tests.conftest import reset_schema, run_alembic

CATALOGO_ESPERADO = ["PENDIENTE", "EN_CURSO", "BLOQUEADA", "HECHA"]


@pytest_asyncio.fixture(autouse=True)
async def base_vacia(db_connection: AsyncConnection):
    await reset_schema(db_connection)
    yield
    await reset_schema(db_connection)


@pytest.mark.asyncio
async def test_upgrade_head_crea_catalogo_de_estados(db_connection: AsyncConnection) -> None:
    result = run_alembic("upgrade", "head")
    assert result.returncode == 0, result.stderr

    rows = (
        await db_connection.execute(text("SELECT code FROM states ORDER BY sort_order, id"))
    ).all()

    assert [row[0] for row in rows] == CATALOGO_ESPERADO


@pytest.mark.asyncio
async def test_migrar_dos_veces_no_duplica(db_connection: AsyncConnection) -> None:
    assert run_alembic("upgrade", "head").returncode == 0
    result = run_alembic("upgrade", "head")
    assert result.returncode == 0, result.stderr

    count = (await db_connection.execute(text("SELECT COUNT(*) FROM states"))).scalar_one()

    assert count == len(CATALOGO_ESPERADO)


@pytest.mark.asyncio
async def test_downgrade_revierte_limpio(db_connection: AsyncConnection) -> None:
    assert run_alembic("upgrade", "head").returncode == 0

    result = run_alembic("downgrade", "base")
    assert result.returncode == 0, result.stderr

    for tabla in ("states", "projects"):
        existe = (
            await db_connection.execute(
                text(
                    "SELECT EXISTS ("
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_name = :tabla"
                    ")"
                ),
                {"tabla": tabla},
            )
        ).scalar_one()

        assert existe is False


@pytest.mark.asyncio
async def test_upgrade_head_crea_tabla_projects_con_columnas_esperadas(
    db_connection: AsyncConnection,
) -> None:
    assert run_alembic("upgrade", "head").returncode == 0

    columnas = (
        await db_connection.execute(
            text(
                "SELECT column_name, data_type, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_name = 'projects'"
            )
        )
    ).all()
    por_nombre = {row.column_name: row for row in columnas}

    assert set(por_nombre) == {"id", "name", "description"}
    assert por_nombre["id"].data_type == "integer"
    assert por_nombre["name"].data_type == "character varying"
    assert por_nombre["name"].is_nullable == "NO"
    assert por_nombre["description"].data_type == "text"
    assert por_nombre["description"].is_nullable == "YES"
