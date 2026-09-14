"""Tests del recurso Tareas v1, conectado a Postgres real.

Corren contra la migración de `tasks` (docs/plan-tareas.md, Incremento 1)
y la conexión compartida de `conftest.py`, según
`docs/decisiones-ingenieria.md`. No cubren `due_at` (v2): eso queda para
los incrementos 5 y 6 del plan, fuera de este archivo por ahora.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db import dispose_engine
from app.main import app
from tests.conftest import reset_schema, run_alembic


@pytest.fixture(autouse=True)
async def tareas_migradas(db_connection: AsyncConnection):
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


async def obtener_id_estado(db_connection: AsyncConnection, code: str) -> int:
    return (
        await db_connection.execute(
            text("SELECT id FROM states WHERE code = :code"), {"code": code}
        )
    ).scalar_one()


async def crear_tarea(client: AsyncClient, **kwargs: object) -> dict:
    response = await client.post("/tasks", json=kwargs)
    assert response.status_code == 201, response.text
    return response.json()


# --- Incremento 3: alta y listado -----------------------------------------


@pytest.mark.asyncio
async def test_post_tasks_devuelve_201_y_esquema_exacto(db_connection: AsyncConnection) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        estado = await obtener_id_estado(db_connection, "PENDIENTE")

        response = await client.post(
            "/tasks",
            json={
                "title": "Regar las plantas",
                "description": "Todos los días",
                "project_id": proyecto["id"],
                "state_id": estado,
            },
        )

    assert response.status_code == 201
    body = response.json()
    # Esquema v3 (docs/contrato-api.md, sección Esquemas de Respuesta):
    # due_at y priority siempre presentes, null si no se fijaron.
    assert set(body.keys()) == {
        "id",
        "title",
        "description",
        "project_id",
        "state_id",
        "due_at",
        "priority",
    }
    assert isinstance(body["id"], int) and body["id"] > 0
    assert body["title"] == "Regar las plantas"
    assert body["description"] == "Todos los días"
    assert body["project_id"] == proyecto["id"]
    assert body["state_id"] == estado
    assert body["due_at"] is None
    assert body["priority"] is None


@pytest.mark.asyncio
async def test_post_tasks_sin_description_la_devuelve_null(db_connection: AsyncConnection) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        estado = await obtener_id_estado(db_connection, "PENDIENTE")

        response = await client.post(
            "/tasks",
            json={"title": "Regar", "project_id": proyecto["id"], "state_id": estado},
        )

    assert response.status_code == 201
    body = response.json()
    assert "description" in body
    assert body["description"] is None


@pytest.mark.asyncio
async def test_post_tasks_titulo_vacio_devuelve_422(db_connection: AsyncConnection) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        estado = await obtener_id_estado(db_connection, "PENDIENTE")

        response = await client.post(
            "/tasks",
            json={"title": "", "project_id": proyecto["id"], "state_id": estado},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_tasks_titulo_solo_espacios_ascii_devuelve_422(
    db_connection: AsyncConnection,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        estado = await obtener_id_estado(db_connection, "PENDIENTE")

        response = await client.post(
            "/tasks",
            json={"title": "   ", "project_id": proyecto["id"], "state_id": estado},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_tasks_titulo_con_invisible_unicode_devuelve_422(
    db_connection: AsyncConnection,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        estado = await obtener_id_estado(db_connection, "PENDIENTE")

        response = await client.post(
            "/tasks",
            json={"title": "​", "project_id": proyecto["id"], "state_id": estado},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_tasks_proyecto_inexistente_devuelve_422(db_connection: AsyncConnection) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        estado = await obtener_id_estado(db_connection, "PENDIENTE")

        response = await client.post(
            "/tasks",
            json={"title": "Regar", "project_id": 999999, "state_id": estado},
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "El proyecto 999999 no existe"}


@pytest.mark.asyncio
async def test_post_tasks_estado_inexistente_devuelve_422() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")

        response = await client.post(
            "/tasks",
            json={"title": "Regar", "project_id": proyecto["id"], "state_id": 999999},
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "El estado 999999 no existe"}


@pytest.mark.asyncio
async def test_get_tasks_lista_vacia() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/tasks")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_tasks_orden_por_id_ascendente_y_estable(db_connection: AsyncConnection) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        estado = await obtener_id_estado(db_connection, "PENDIENTE")

        creadas = [
            await crear_tarea(client, title="A", project_id=proyecto["id"], state_id=estado),
            await crear_tarea(client, title="B", project_id=proyecto["id"], state_id=estado),
            await crear_tarea(client, title="C", project_id=proyecto["id"], state_id=estado),
        ]
        ids_esperados = [t["id"] for t in creadas]

        primera = (await client.get("/tasks")).json()
        segunda = (await client.get("/tasks")).json()

    assert [t["id"] for t in primera] == sorted(ids_esperados)
    assert primera == segunda


@pytest.mark.asyncio
async def test_get_tasks_filtra_por_project_id_y_state_id_solos_y_combinados(
    db_connection: AsyncConnection,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto_a = await crear_proyecto(client, name="Casa")
        proyecto_b = await crear_proyecto(client, name="Trabajo")
        pendiente = await obtener_id_estado(db_connection, "PENDIENTE")
        en_curso = await obtener_id_estado(db_connection, "EN_CURSO")

        tarea_a_pendiente = await crear_tarea(
            client, title="A-pendiente", project_id=proyecto_a["id"], state_id=pendiente
        )
        await crear_tarea(
            client, title="A-en_curso", project_id=proyecto_a["id"], state_id=en_curso
        )
        await crear_tarea(
            client, title="B-pendiente", project_id=proyecto_b["id"], state_id=pendiente
        )

        solo_proyecto = (
            await client.get("/tasks", params={"project_id": proyecto_a["id"]})
        ).json()
        solo_estado = (await client.get("/tasks", params={"state_id": pendiente})).json()
        combinado = (
            await client.get(
                "/tasks",
                params={"project_id": proyecto_a["id"], "state_id": pendiente},
            )
        ).json()

    assert len(solo_proyecto) == 2
    assert len(solo_estado) == 2
    assert combinado == [tarea_a_pendiente]


# --- Incremento 4: lectura, actualización y borrado -----------------------


@pytest.mark.asyncio
async def test_get_task_by_id_existente(db_connection: AsyncConnection) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        estado = await obtener_id_estado(db_connection, "PENDIENTE")
        creada = await crear_tarea(
            client, title="Regar", project_id=proyecto["id"], state_id=estado
        )

        response = await client.get(f"/tasks/{creada['id']}")

    assert response.status_code == 200
    assert response.json() == creada


@pytest.mark.asyncio
async def test_get_task_by_id_inexistente_devuelve_404() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/tasks/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Tarea no encontrada"}


@pytest.mark.asyncio
async def test_patch_task_solo_title(db_connection: AsyncConnection) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        estado = await obtener_id_estado(db_connection, "PENDIENTE")
        creada = await crear_tarea(
            client, title="Regar", project_id=proyecto["id"], state_id=estado
        )

        response = await client.patch(f"/tasks/{creada['id']}", json={"title": "Regar todo"})

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Regar todo"
    assert body["project_id"] == proyecto["id"]
    assert body["state_id"] == estado


@pytest.mark.asyncio
async def test_patch_task_solo_description(db_connection: AsyncConnection) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        estado = await obtener_id_estado(db_connection, "PENDIENTE")
        creada = await crear_tarea(
            client, title="Regar", project_id=proyecto["id"], state_id=estado
        )

        response = await client.patch(
            f"/tasks/{creada['id']}", json={"description": "Todos los días"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Regar"
    assert body["description"] == "Todos los días"


@pytest.mark.asyncio
async def test_patch_task_project_id_y_state_id(db_connection: AsyncConnection) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto_a = await crear_proyecto(client, name="Casa")
        proyecto_b = await crear_proyecto(client, name="Trabajo")
        pendiente = await obtener_id_estado(db_connection, "PENDIENTE")
        en_curso = await obtener_id_estado(db_connection, "EN_CURSO")
        creada = await crear_tarea(
            client, title="Regar", project_id=proyecto_a["id"], state_id=pendiente
        )

        response = await client.patch(
            f"/tasks/{creada['id']}",
            json={"project_id": proyecto_b["id"], "state_id": en_curso},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == proyecto_b["id"]
    assert body["state_id"] == en_curso


@pytest.mark.asyncio
async def test_patch_task_sin_campos_no_cambia_nada(db_connection: AsyncConnection) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        estado = await obtener_id_estado(db_connection, "PENDIENTE")
        creada = await crear_tarea(
            client, title="Regar", project_id=proyecto["id"], state_id=estado
        )

        response = await client.patch(f"/tasks/{creada['id']}", json={})

    assert response.status_code == 200
    assert response.json() == creada


@pytest.mark.asyncio
async def test_patch_task_project_id_inexistente_devuelve_422(
    db_connection: AsyncConnection,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        estado = await obtener_id_estado(db_connection, "PENDIENTE")
        creada = await crear_tarea(
            client, title="Regar", project_id=proyecto["id"], state_id=estado
        )

        response = await client.patch(f"/tasks/{creada['id']}", json={"project_id": 999999})

    assert response.status_code == 422
    assert response.json() == {"detail": "El proyecto 999999 no existe"}


@pytest.mark.asyncio
async def test_patch_task_inexistente_devuelve_404() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch("/tasks/999999", json={"title": "Nuevo"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Tarea no encontrada"}


@pytest.mark.asyncio
async def test_delete_task_existente_devuelve_204_sin_cuerpo(
    db_connection: AsyncConnection,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        estado = await obtener_id_estado(db_connection, "PENDIENTE")
        creada = await crear_tarea(
            client, title="Regar", project_id=proyecto["id"], state_id=estado
        )

        response = await client.delete(f"/tasks/{creada['id']}")

    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.asyncio
async def test_delete_task_luego_get_devuelve_404(db_connection: AsyncConnection) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        estado = await obtener_id_estado(db_connection, "PENDIENTE")
        creada = await crear_tarea(
            client, title="Regar", project_id=proyecto["id"], state_id=estado
        )

        await client.delete(f"/tasks/{creada['id']}")
        response = await client.get(f"/tasks/{creada['id']}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_task_inexistente_devuelve_404() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete("/tasks/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Tarea no encontrada"}


# --- Incremento 6: validación, esquema y overdue de due_at ----------------


@pytest.mark.asyncio
async def test_post_tasks_sin_due_at_lo_devuelve_null(db_connection: AsyncConnection) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        estado = await obtener_id_estado(db_connection, "PENDIENTE")

        response = await client.post(
            "/tasks",
            json={"title": "Regar", "project_id": proyecto["id"], "state_id": estado},
        )

    assert response.status_code == 201
    assert response.json()["due_at"] is None


@pytest.mark.asyncio
async def test_post_tasks_due_at_valido_se_normaliza_a_utc_sin_microsegundos(
    db_connection: AsyncConnection,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        estado = await obtener_id_estado(db_connection, "PENDIENTE")

        # Con desplazamiento (+02:00) y microsegundos, para verificar que
        # la API normaliza a UTC y recorta a segundos enteros al serializar.
        response = await client.post(
            "/tasks",
            json={
                "title": "Regar",
                "project_id": proyecto["id"],
                "state_id": estado,
                "due_at": "2030-06-15T12:30:00.123456+02:00",
            },
        )

    assert response.status_code == 201
    assert response.json()["due_at"] == "2030-06-15T10:30:00Z"


@pytest.mark.asyncio
async def test_post_tasks_due_at_sin_zona_devuelve_422(db_connection: AsyncConnection) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        estado = await obtener_id_estado(db_connection, "PENDIENTE")

        response = await client.post(
            "/tasks",
            json={
                "title": "Regar",
                "project_id": proyecto["id"],
                "state_id": estado,
                "due_at": "2030-06-15T12:30:00",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_patch_tasks_due_at_sin_zona_devuelve_422(db_connection: AsyncConnection) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        estado = await obtener_id_estado(db_connection, "PENDIENTE")
        creada = await crear_tarea(
            client, title="Regar", project_id=proyecto["id"], state_id=estado
        )

        response = await client.patch(
            f"/tasks/{creada['id']}", json={"due_at": "2030-06-15T12:30:00"}
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_tasks_overdue_true_devuelve_solo_vencidas_y_no_hechas(
    db_connection: AsyncConnection,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto = await crear_proyecto(client, name="Casa")
        pendiente = await obtener_id_estado(db_connection, "PENDIENTE")
        hecha = await obtener_id_estado(db_connection, "HECHA")

        sin_fecha = await crear_tarea(
            client, title="Sin fecha", project_id=proyecto["id"], state_id=pendiente
        )
        vencida = await crear_tarea(
            client,
            title="Vencida",
            project_id=proyecto["id"],
            state_id=pendiente,
            due_at="2020-01-01T00:00:00Z",
        )
        futura = await crear_tarea(
            client,
            title="Futura",
            project_id=proyecto["id"],
            state_id=pendiente,
            due_at="2999-01-01T00:00:00Z",
        )
        vencida_hecha = await crear_tarea(
            client,
            title="Vencida pero hecha",
            project_id=proyecto["id"],
            state_id=hecha,
            due_at="2020-01-01T00:00:00Z",
        )

        response = await client.get("/tasks", params={"overdue": "true"})

    assert response.status_code == 200
    ids_devueltos = {t["id"] for t in response.json()}
    assert ids_devueltos == {vencida["id"]}
    assert sin_fecha["id"] not in ids_devueltos
    assert futura["id"] not in ids_devueltos
    assert vencida_hecha["id"] not in ids_devueltos


@pytest.mark.asyncio
async def test_get_tasks_overdue_combinado_con_project_id(db_connection: AsyncConnection) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        proyecto_a = await crear_proyecto(client, name="Casa")
        proyecto_b = await crear_proyecto(client, name="Trabajo")
        pendiente = await obtener_id_estado(db_connection, "PENDIENTE")

        vencida_a = await crear_tarea(
            client,
            title="Vencida A",
            project_id=proyecto_a["id"],
            state_id=pendiente,
            due_at="2020-01-01T00:00:00Z",
        )
        await crear_tarea(
            client,
            title="Vencida B",
            project_id=proyecto_b["id"],
            state_id=pendiente,
            due_at="2020-01-01T00:00:00Z",
        )

        response = await client.get(
            "/tasks", params={"overdue": "true", "project_id": proyecto_a["id"]}
        )

    assert response.status_code == 200
    assert [t["id"] for t in response.json()] == [vencida_a["id"]]
