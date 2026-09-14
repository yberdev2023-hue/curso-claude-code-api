"""agrega priority a tareas

Revision ID: 46b76baf6331
Revises: 7933dbf104b4
Create Date: 2026-09-13 22:03:02.759547

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '46b76baf6331'
down_revision: str | Sequence[str] | None = '7933dbf104b4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # docs/contrato-api.md, sección Tareas v3: Prioridad. Entero opcional
    # (1 a 5); el rango se valida en la aplicación (app/schemas.py), no acá.
    op.add_column("tasks", sa.Column("priority", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("tasks", "priority")
