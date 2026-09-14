"""revision vacia sin cambios de esquema

Revision ID: 22b284242167
Revises: dbc0994c8481
Create Date: 2026-09-13 20:45:50.814504

"""
from collections.abc import Sequence

import sqlalchemy as sa  # noqa: F401

from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = '22b284242167'
down_revision: str | Sequence[str] | None = 'dbc0994c8481'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
