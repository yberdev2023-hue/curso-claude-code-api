"""Tests de la migración inicial: tabla de estados + seed idempotente.

Corren contra Postgres real (la instancia de `compose.yaml`), nunca contra
SQLite ni mocks, según `docs/decisiones-ingenieria.md`. Manejan Alembic vía
subprocess para poder validar el ciclo completo upgrade/downgrade tal como
lo ve un usuario del CLI, y limpian el esquema de versiones de Alembic antes
y después de cada prueba para partir de una base vacía.
"""

import subprocess
import sys

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.settings import get_database_url

CATALOGO_ESPERADO = ["PENDIENTE", "EN_CURSO", "BLOQUEADA", "HECHA"]


def run_alembic(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        capture_output=True,
        text=True,
    )


async def reset_schema() -> None:
    engine = create_async_engine(get_database_url())
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS states"))
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    await engine.dispose()


@pytest.fixture(autouse=True)
async def base_vacia():
    await reset_schema()
    yield
    await reset_schema()


@pytest.mark.asyncio
async def test_upgrade_head_crea_catalogo_de_estados() -> None:
    result = run_alembic("upgrade", "head")
    assert result.returncode == 0, result.stderr

    engine = create_async_engine(get_database_url())
    async with engine.connect() as conn:
        rows = (
            await conn.execute(text("SELECT code FROM states ORDER BY sort_order, id"))
        ).all()
    await engine.dispose()

    assert [row[0] for row in rows] == CATALOGO_ESPERADO


@pytest.mark.asyncio
async def test_migrar_dos_veces_no_duplica() -> None:
    assert run_alembic("upgrade", "head").returncode == 0
    result = run_alembic("upgrade", "head")
    assert result.returncode == 0, result.stderr

    engine = create_async_engine(get_database_url())
    async with engine.connect() as conn:
        count = (await conn.execute(text("SELECT COUNT(*) FROM states"))).scalar_one()
    await engine.dispose()

    assert count == len(CATALOGO_ESPERADO)


@pytest.mark.asyncio
async def test_downgrade_revierte_limpio() -> None:
    assert run_alembic("upgrade", "head").returncode == 0

    result = run_alembic("downgrade", "base")
    assert result.returncode == 0, result.stderr

    engine = create_async_engine(get_database_url())
    async with engine.connect() as conn:
        existe = (
            await conn.execute(
                text(
                    "SELECT EXISTS ("
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_name = 'states'"
                    ")"
                )
            )
        ).scalar_one()
    await engine.dispose()

    assert existe is False
