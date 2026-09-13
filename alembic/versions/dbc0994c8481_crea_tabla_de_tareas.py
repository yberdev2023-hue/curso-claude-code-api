"""crea tabla de tareas

Revision ID: dbc0994c8481
Revises: fd59bbd33189
Create Date: 2026-09-13 15:37:44.132580

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'dbc0994c8481'
down_revision: str | Sequence[str] | None = 'fd59bbd33189'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False
        ),
        sa.Column(
            "state_id", sa.Integer(), sa.ForeignKey("states.id"), nullable=False
        ),
    )
    # Postgres no indexa columnas de FK por defecto; GET /tasks filtra por
    # ambas (docs/contrato-api.md, sección Tareas v1).
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"])
    op.create_index("ix_tasks_state_id", "tasks", ["state_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_tasks_state_id", table_name="tasks")
    op.drop_index("ix_tasks_project_id", table_name="tasks")
    op.drop_table("tasks")
