"""add server default to created_at

Revision ID: 474e08917fca
Revises: a654b6a854ba
Create Date: 2026-10-14 15:18:07.182956

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '474e08917fca'
down_revision: Union[str, Sequence[str], None] = 'a654b6a854ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("reference_library", "created_at", server_default=sa.text("now()"))
    op.alter_column("classification_logs", "created_at", server_default=sa.text("now()"))
    op.alter_column("corrections", "created_at", server_default=sa.text("now()"))


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("reference_library", "created_at", server_default=None)
    op.alter_column("classification_logs", "created_at", server_default=None)
    op.alter_column("corrections", "created_at", server_default=None)
