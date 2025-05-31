"""Merge migration heads

Revision ID: 067be40dce55
Revises: add_is_archived_column, b652b602394e
Create Date: 2025-05-31 19:50:54.831913

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '067be40dce55'
down_revision: Union[str, None] = ('add_is_archived_column', 'b652b602394e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
