"""Remove is_active from schedules

Revision ID: remove_schedule_is_active
Revises: 378ba4f11d45
Create Date: 2024-01-29 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'remove_schedule_is_active'
down_revision: Union[str, None] = '378ba4f11d45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the is_active column from schedules table
    op.drop_column('schedules', 'is_active')


def downgrade() -> None:
    # Add back the is_active column with default value True
    op.add_column('schedules',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true')
    ) 