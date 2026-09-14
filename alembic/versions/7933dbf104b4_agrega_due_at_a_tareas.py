"""agrega due_at a tareas

Revision ID: 7933dbf104b4
Revises: 22b284242167
Create Date: 2026-09-13 21:31:29.012317

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7933dbf104b4'
down_revision: str | Sequence[str] | None = '22b284242167'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # docs/contrato-api.md, sección Tareas v2: Fechas Límite. `due_at` es
    # opcional (nullable) y se guarda con zona horaria (TIMESTAMPTZ):
    # omitirlo conserva compatibilidad v1.
    op.add_column("tasks", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("tasks", "due_at")
