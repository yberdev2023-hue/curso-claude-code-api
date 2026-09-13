"""Tests de la migración inicial: tabla de estados + seed idempotente.

Corren contra Postgres real (la instancia de `compose.yaml`), nunca contra
SQLite ni mocks, según `docs/decisiones-ingenieria.md`, usando la conexión
compartida de `conftest.py`. Manejan Alembic vía subprocess para poder
validar el ciclo completo upgrade/downgrade tal como lo ve un usuario del
CLI, y limpian el esquema de versiones de Alembic antes y después de cada
prueba para partir de una base vacía.
"""

import subprocess
import sys

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

CATALOGO_ESPERADO = ["PENDIENTE", "EN_CURSO", "BLOQUEADA", "HECHA"]


def run_alembic(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        capture_output=True,
        text=True,
    )


async def reset_schema(conn: AsyncConnection) -> None:
    await conn.execute(text("DROP TABLE IF EXISTS states"))
    await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    await conn.commit()


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

    existe = (
        await db_connection.execute(
            text(
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'states'"
                ")"
            )
        )
    ).scalar_one()

    assert existe is False
