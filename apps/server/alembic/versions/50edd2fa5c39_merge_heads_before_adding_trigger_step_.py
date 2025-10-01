"""Merge heads before adding trigger step type to area_steps

Revision ID: 50edd2fa5c39
Revises: 202509301200, 202509301812, 202510010335
Create Date: 2025-10-01 15:59:00.426022

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '50edd2fa5c39'
down_revision: Union[str, None] = ('202509301200', '202509301812', '202510010335')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
