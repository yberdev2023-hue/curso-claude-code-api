from fastapi import FastAPI
from sqlalchemy import text

from app.db import get_engine

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
