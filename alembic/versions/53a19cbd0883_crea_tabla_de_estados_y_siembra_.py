"""crea tabla de estados y siembra catalogo fijo

Revision ID: 53a19cbd0883
Revises:
Create Date: 2026-09-10 00:33:16.340623

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '53a19cbd0883'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Catálogo fijo definido en docs/contrato-api.md (sección Estados). No tiene
# endpoints propios: se siembra por migración para que exista antes de la
# primera petición, en cualquier entorno.
CATALOGO_ESTADOS = [
    (1, "PENDIENTE"),
    (2, "EN_CURSO"),
    (3, "BLOQUEADA"),
    (4, "HECHA"),
]

states_table = sa.table(
    "states",
    sa.column("id", sa.Integer),
    sa.column("code", sa.String),
    sa.column("sort_order", sa.Integer),
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=20), nullable=False, unique=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, unique=True),
    )

    # Seed idempotente: ON CONFLICT DO NOTHING hace que aplicar el upgrade
    # más de una vez deje el mismo catálogo, sin duplicar filas.
    insert_stmt = sa.dialects.postgresql.insert(states_table).values(
        [
            {"id": id_, "code": code, "sort_order": sort_order}
            for sort_order, (id_, code) in enumerate(CATALOGO_ESTADOS, start=1)
        ]
    )
    op.execute(insert_stmt.on_conflict_do_nothing(index_elements=["id"]))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("states")
