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

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.settings import get_database_url


@pytest_asyncio.fixture
async def db_connection() -> AsyncConnection:
    """Conexión async de vida corta (una por test) contra Postgres real."""
    engine = create_async_engine(get_database_url())
    async with engine.connect() as connection:
        yield connection
    await engine.dispose()
