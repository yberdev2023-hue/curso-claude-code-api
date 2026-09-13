from fastapi import FastAPI, HTTPException, status
from sqlalchemy import text

from app.db import get_engine
from app.schemas import ProjectCreate, ProjectUpdate

app = FastAPI(title="TaskFlow API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/states")
async def list_states() -> list[dict[str, object]]:
    async with get_engine().connect() as conn:
        rows = await conn.execute(
            text("SELECT id, code FROM states ORDER BY sort_order, id")
        )
        return [{"id": row.id, "code": row.code} for row in rows]


def _project_row_to_dict(row) -> dict[str, object]:
    return {"id": row.id, "name": row.name, "description": row.description}


@app.post("/projects", status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate) -> dict[str, object]:
    async with get_engine().begin() as conn:
        row = (
            await conn.execute(
                text(
                    "INSERT INTO projects (name, description) "
                    "VALUES (:name, :description) "
                    "RETURNING id, name, description"
                ),
                {"name": payload.name, "description": payload.description},
            )
        ).one()
    return _project_row_to_dict(row)


@app.get("/projects")
async def list_projects() -> list[dict[str, object]]:
    async with get_engine().connect() as conn:
        rows = await conn.execute(
            text("SELECT id, name, description FROM projects ORDER BY id")
        )
        return [_project_row_to_dict(row) for row in rows]


@app.get("/projects/{project_id}")
async def get_project(project_id: int) -> dict[str, object]:
    async with get_engine().connect() as conn:
        row = (
            await conn.execute(
                text("SELECT id, name, description FROM projects WHERE id = :id"),
                {"id": project_id},
            )
        ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return _project_row_to_dict(row)


@app.patch("/projects/{project_id}")
async def update_project(project_id: int, payload: ProjectUpdate) -> dict[str, object]:
    cambios = payload.model_dump(exclude_unset=True)
    async with get_engine().begin() as conn:
        if cambios:
            # Las claves de `cambios` vienen únicamente de los campos
            # declarados en ProjectUpdate (name/description), nunca de
            # entrada arbitraria del cliente, así que el f-string en el
            # SET es seguro frente a inyección.
            set_clause = ", ".join(f"{campo} = :{campo}" for campo in cambios)
            row = (
                await conn.execute(
                    text(
                        f"UPDATE projects SET {set_clause} WHERE id = :id "
                        "RETURNING id, name, description"
                    ),
                    {**cambios, "id": project_id},
                )
            ).one_or_none()
        else:
            row = (
                await conn.execute(
                    text("SELECT id, name, description FROM projects WHERE id = :id"),
                    {"id": project_id},
                )
            ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return _project_row_to_dict(row)


@app.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: int) -> None:
    # docs/contrato-api.md, sección Proyectos: "409 si tiene tareas". La
    # tabla `tasks` ya existe (docs/plan-tareas.md, Incremento 1), así que
    # este chequeo cierra el diferimiento que dejó docs/plan-proyectos.md.
    async with get_engine().begin() as conn:
        tiene_tareas = (
            await conn.execute(
                text("SELECT EXISTS (SELECT 1 FROM tasks WHERE project_id = :id)"),
                {"id": project_id},
            )
        ).scalar_one()
        if tiene_tareas:
            raise HTTPException(
                status_code=409, detail="El proyecto tiene tareas asociadas"
            )
        result = await conn.execute(
            text("DELETE FROM projects WHERE id = :id"), {"id": project_id}
        )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
