"""Add timezone support to timestamp columns

Revision ID: add_timezone_to_timestamps
Revises: remove_schedule_is_active
Create Date: 2024-02-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


# revision identifiers, used by Alembic.
revision: str = 'add_timezone_to_timestamps'
down_revision: Union[str, None] = 'remove_schedule_is_active'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite doesn't support altering columns directly, so we need to:
    # 1. Create new tables with timezone support
    # 2. Copy data from old tables
    # 3. Drop old tables
    # 4. Rename new tables to original names
    
    # Scripts table
    with op.batch_alter_table('scripts', schema=None) as batch_op:
        batch_op.alter_column('created_at',
                            existing_type=sa.DateTime(),
                            type_=sa.DateTime(timezone=True),
                            existing_nullable=True)
        batch_op.alter_column('updated_at',
                            existing_type=sa.DateTime(),
                            type_=sa.DateTime(timezone=True),
                            existing_nullable=True)
    
    # Executions table
    with op.batch_alter_table('executions', schema=None) as batch_op:
        batch_op.alter_column('started_at',
                            existing_type=sa.DateTime(),
                            type_=sa.DateTime(timezone=True),
                            existing_nullable=True)
        batch_op.alter_column('completed_at',
                            existing_type=sa.DateTime(),
                            type_=sa.DateTime(timezone=True),
                            existing_nullable=True)
    
    # Schedules table
    with op.batch_alter_table('schedules', schema=None) as batch_op:
        batch_op.alter_column('created_at',
                            existing_type=sa.DateTime(),
                            type_=sa.DateTime(timezone=True),
                            existing_nullable=True)


def downgrade() -> None:
    # Remove timezone support from timestamp columns
    with op.batch_alter_table('scripts', schema=None) as batch_op:
        batch_op.alter_column('created_at',
                            existing_type=sa.DateTime(timezone=True),
                            type_=sa.DateTime(),
                            existing_nullable=True)
        batch_op.alter_column('updated_at',
                            existing_type=sa.DateTime(timezone=True),
                            type_=sa.DateTime(),
                            existing_nullable=True)
    
    with op.batch_alter_table('executions', schema=None) as batch_op:
        batch_op.alter_column('started_at',
                            existing_type=sa.DateTime(timezone=True),
                            type_=sa.DateTime(),
                            existing_nullable=True)
        batch_op.alter_column('completed_at',
                            existing_type=sa.DateTime(timezone=True),
                            type_=sa.DateTime(),
                            existing_nullable=True)
    
    with op.batch_alter_table('schedules', schema=None) as batch_op:
        batch_op.alter_column('created_at',
                            existing_type=sa.DateTime(timezone=True),
                            type_=sa.DateTime(),
                            existing_nullable=True) 