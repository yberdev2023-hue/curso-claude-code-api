"""crea tabla de proyectos

Revision ID: fd59bbd33189
Revises: 53a19cbd0883
Create Date: 2026-09-13 12:09:38.036967

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'fd59bbd33189'
down_revision: str | Sequence[str] | None = '53a19cbd0883'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )
    # Sin seed: a diferencia de `states`, Proyectos no es un catálogo
    # cerrado. Los registros los crea la API vía POST /projects.


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("projects")
