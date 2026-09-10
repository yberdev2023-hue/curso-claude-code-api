"""Configuración de conexión a la base de datos.

Los valores se leen de variables de entorno con los nombres documentados en
`.env.example` (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT).
Este módulo no abre ni lee `.env` directamente: `os.environ` ya refleja lo
que el proceso tenga cargado (por ejemplo, vía `docker compose` o el propio
entorno de ejecución).
"""

import os

POSTGRES_USER = os.environ.get("POSTGRES_USER", "taskflow")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "taskflow_dev_password")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "taskflow")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")


def get_database_url(*, driver: str = "asyncpg") -> str:
    """Arma la URL de conexión SQLAlchemy a partir de las variables de entorno."""
    return (
        f"postgresql+{driver}://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
