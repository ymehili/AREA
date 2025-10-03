"""merge migration heads

Revision ID: fc5760e6871a
Revises: 202510011200, 6b0e6164fb95
Create Date: 2025-10-02 06:12:32.827041

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc5760e6871a'
down_revision: Union[str, None] = ('202510011200', '6b0e6164fb95')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
