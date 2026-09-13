"""Engine de base de datos de la aplicación.

Usa la misma URL de conexión que Alembic (`app.settings.get_database_url`),
construida a partir de variables de entorno con los nombres documentados en
`.env.example`, sin abrir `.env`.

El engine se resuelve de forma perezosa y cacheada (no a nivel de módulo)
para que un test pueda liberarlo con `dispose_engine()` entre corridas: una
conexión asyncpg queda atada al event loop en el que se creó, y
pytest-asyncio abre un loop nuevo por test.
"""

from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.settings import get_database_url


@lru_cache
def get_engine() -> AsyncEngine:
    """Engine async de la aplicación, creado una vez por event loop activo."""
    return create_async_engine(get_database_url())


async def dispose_engine() -> None:
    """Cierra y descarta el engine cacheado. Uso: entre tests que cambian de event loop."""
    if get_engine.cache_info().currsize:
        await get_engine().dispose()
    get_engine.cache_clear()
