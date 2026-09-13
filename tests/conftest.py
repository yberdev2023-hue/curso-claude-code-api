"""Fixtures compartidas para tests de persistencia.

Los tests de persistencia corren contra Postgres real (la instancia de
`compose.yaml`), nunca contra SQLite ni mocks, según
`docs/decisiones-ingenieria.md`. Este módulo centraliza la conexión async
para que cada test no arme la suya.

El engine se crea por test (no por sesión): pytest-asyncio abre un event
loop nuevo en cada test, y un engine/conexión asyncpg queda atado al loop
en el que se creó, así que compartirlo entre tests con loops distintos
rompe con "another operation is in progress" o "Event loop is closed".
"""

import subprocess
import sys
from collections.abc import Sequence

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.settings import get_database_url

# Todas las tablas creadas por migraciones hasta hoy, en orden de borrado
# seguro: `tasks` tiene FKs hacia `projects` y `states`, así que debe
# dropearse primero. Agregar acá cada tabla nueva evita que un test
# posterior falle con "relation already exists" por un residuo de una
# corrida interrumpida.
TABLAS_GESTIONADAS = ("tasks", "projects", "states")


@pytest_asyncio.fixture
async def db_connection() -> AsyncConnection:
    """Conexión async de vida corta (una por test) contra Postgres real."""
    engine = create_async_engine(get_database_url())
    async with engine.connect() as connection:
        yield connection
    await engine.dispose()


def run_alembic(*args: str) -> subprocess.CompletedProcess:
    """Invoca Alembic vía subprocess, igual que lo vería un usuario del CLI."""
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        capture_output=True,
        text=True,
    )


async def reset_schema(
    conn: AsyncConnection, *, tablas: Sequence[str] = TABLAS_GESTIONADAS
) -> None:
    """Deja la base sin las tablas gestionadas por Alembic ni su tabla de versiones."""
    for tabla in tablas:
        await conn.execute(text(f"DROP TABLE IF EXISTS {tabla}"))
    await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    await conn.commit()
