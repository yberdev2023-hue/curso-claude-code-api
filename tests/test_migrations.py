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
from sqlalchemy.exc import IntegrityError
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

    for tabla in ("states", "projects", "tasks"):
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


@pytest.mark.asyncio
async def test_upgrade_head_crea_tabla_tasks_con_columnas_y_fks_esperadas(
    db_connection: AsyncConnection,
) -> None:
    # Se sube exactamente a la migración de tareas v1 (Incremento 1 de
    # docs/plan-tareas.md), no a `head`: desde que existe la migración de
    # `due_at` (Incremento 5), `head` ya no coincide con el estado que este
    # test verifica. El comportamiento de esa migración puntual no cambió.
    assert run_alembic("upgrade", "dbc0994c8481").returncode == 0

    columnas = (
        await db_connection.execute(
            text(
                "SELECT column_name, data_type, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_name = 'tasks'"
            )
        )
    ).all()
    por_nombre = {row.column_name: row for row in columnas}

    assert set(por_nombre) == {"id", "title", "description", "project_id", "state_id"}
    assert por_nombre["id"].data_type == "integer"
    assert por_nombre["title"].data_type == "character varying"
    assert por_nombre["title"].is_nullable == "NO"
    assert por_nombre["description"].data_type == "text"
    assert por_nombre["description"].is_nullable == "YES"
    assert por_nombre["project_id"].data_type == "integer"
    assert por_nombre["project_id"].is_nullable == "NO"
    assert por_nombre["state_id"].data_type == "integer"
    assert por_nombre["state_id"].is_nullable == "NO"

    fks = (
        await db_connection.execute(
            text(
                "SELECT ccu.table_name AS tabla_referenciada "
                "FROM information_schema.table_constraints tc "
                "JOIN information_schema.constraint_column_usage ccu "
                "ON tc.constraint_name = ccu.constraint_name "
                "WHERE tc.table_name = 'tasks' AND tc.constraint_type = 'FOREIGN KEY'"
            )
        )
    ).all()

    assert {row.tabla_referenciada for row in fks} == {"projects", "states"}


@pytest.mark.asyncio
async def test_borrar_proyecto_o_estado_referenciado_por_tarea_falla(
    db_connection: AsyncConnection,
) -> None:
    assert run_alembic("upgrade", "head").returncode == 0

    proyecto = (
        await db_connection.execute(
            text(
                "INSERT INTO projects (name) VALUES ('Casa') RETURNING id"
            )
        )
    ).scalar_one()
    estado = (
        await db_connection.execute(text("SELECT id FROM states WHERE code = 'PENDIENTE'"))
    ).scalar_one()
    await db_connection.execute(
        text(
            "INSERT INTO tasks (title, project_id, state_id) "
            "VALUES ('Regar las plantas', :project_id, :state_id)"
        ),
        {"project_id": proyecto, "state_id": estado},
    )
    await db_connection.commit()

    with pytest.raises(IntegrityError):
        await db_connection.execute(text("DELETE FROM projects WHERE id = :id"), {"id": proyecto})
    await db_connection.rollback()


@pytest.mark.asyncio
async def test_upgrade_head_agrega_due_at_a_tasks(db_connection: AsyncConnection) -> None:
    assert run_alembic("upgrade", "head").returncode == 0

    columna = (
        await db_connection.execute(
            text(
                "SELECT data_type, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_name = 'tasks' AND column_name = 'due_at'"
            )
        )
    ).one()

    assert columna.data_type == "timestamp with time zone"
    assert columna.is_nullable == "YES"


@pytest.mark.asyncio
async def test_downgrade_de_due_at_revierte_limpio_sin_afectar_el_resto_de_tasks(
    db_connection: AsyncConnection,
) -> None:
    assert run_alembic("upgrade", "head").returncode == 0

    # Un paso atrás: revierte solo la migración de due_at (Incremento 5 de
    # docs/plan-tareas.md), no toda la cadena, según la Matriz Mínima de
    # Tests ("rollback de v2").
    result = run_alembic("downgrade", "-1")
    assert result.returncode == 0, result.stderr

    columnas = (
        await db_connection.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'tasks'"
            )
        )
    ).all()
    nombres = {row.column_name for row in columnas}

    assert "due_at" not in nombres
    assert nombres == {"id", "title", "description", "project_id", "state_id"}
