"""merge heads

Revision ID: 830e69042411
Revises: 202412211500, 202509291800
Create Date: 2025-09-29 21:39:18.098493

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '830e69042411'
down_revision: Union[str, None] = ('202412211500', '202509291800')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
