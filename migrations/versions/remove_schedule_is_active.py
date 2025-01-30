"""Remove is_active from schedules

Revision ID: remove_schedule_is_active
Revises: 378ba4f11d45
Create Date: 2024-01-29 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = 'remove_schedule_is_active'
down_revision: Union[str, None] = '378ba4f11d45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in the specified table."""
    inspector = Inspector.from_engine(op.get_bind())
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Only drop the is_active column if it exists
    if column_exists('schedules', 'is_active'):
        with op.batch_alter_table('schedules', schema=None) as batch_op:
            batch_op.drop_column('is_active')


def downgrade() -> None:
    # Only add the is_active column if it doesn't exist
    if not column_exists('schedules', 'is_active'):
        with op.batch_alter_table('schedules', schema=None) as batch_op:
            batch_op.add_column(
                sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true')
            ) 