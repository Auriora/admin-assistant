"""Merge account context and backup configurations

Revision ID: df594ad7fd1d
Revises: 20250610_add_account_context_to_uris, d0c8b7242357
Create Date: 2025-06-10 20:58:20.432017

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'df594ad7fd1d'
down_revision: Union[str, None] = ('20250610_add_account_context_to_uris', 'd0c8b7242357')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
