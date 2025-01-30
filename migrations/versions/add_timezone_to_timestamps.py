"""Add timezone support to timestamp columns

Revision ID: add_timezone_to_timestamps
Revises: remove_schedule_is_active
Create Date: 2024-02-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.engine import Connection
from datetime import datetime, timezone


# revision identifiers, used by Alembic.
revision: str = 'add_timezone_to_timestamps'
down_revision: Union[str, None] = 'remove_schedule_is_active'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def get_column_type(conn: Connection, table: str, column: str) -> str:
    """Get the current type of a column."""
    inspector = Inspector.from_engine(conn)
    for col in inspector.get_columns(table):
        if col['name'] == column:
            return str(col['type'])
    return None


def upgrade() -> None:
    # Get database connection
    connection = op.get_bind()
    
    # Scripts table
    with op.batch_alter_table('scripts', schema=None) as batch_op:
        # Only modify if the column exists and isn't already timezone-aware
        if get_column_type(connection, 'scripts', 'created_at') == 'DATETIME':
            batch_op.alter_column('created_at',
                                existing_type=sa.DateTime(),
                                type_=sa.DateTime(timezone=True),
                                existing_nullable=True,
                                postgresql_using='created_at AT TIME ZONE \'UTC\'')
        if get_column_type(connection, 'scripts', 'updated_at') == 'DATETIME':
            batch_op.alter_column('updated_at',
                                existing_type=sa.DateTime(),
                                type_=sa.DateTime(timezone=True),
                                existing_nullable=True,
                                postgresql_using='updated_at AT TIME ZONE \'UTC\'')
    
    # Executions table
    with op.batch_alter_table('executions', schema=None) as batch_op:
        if get_column_type(connection, 'executions', 'started_at') == 'DATETIME':
            batch_op.alter_column('started_at',
                                existing_type=sa.DateTime(),
                                type_=sa.DateTime(timezone=True),
                                existing_nullable=True,
                                postgresql_using='started_at AT TIME ZONE \'UTC\'')
        if get_column_type(connection, 'executions', 'completed_at') == 'DATETIME':
            batch_op.alter_column('completed_at',
                                existing_type=sa.DateTime(),
                                type_=sa.DateTime(timezone=True),
                                existing_nullable=True,
                                postgresql_using='completed_at AT TIME ZONE \'UTC\'')
    
    # Schedules table
    with op.batch_alter_table('schedules', schema=None) as batch_op:
        if get_column_type(connection, 'schedules', 'created_at') == 'DATETIME':
            batch_op.alter_column('created_at',
                                existing_type=sa.DateTime(),
                                type_=sa.DateTime(timezone=True),
                                existing_nullable=True,
                                postgresql_using='created_at AT TIME ZONE \'UTC\'')


def downgrade() -> None:
    connection = op.get_bind()
    
    # Remove timezone support from timestamp columns only if they are timezone-aware
    with op.batch_alter_table('scripts', schema=None) as batch_op:
        if get_column_type(connection, 'scripts', 'created_at') == 'DATETIME WITH TIME ZONE':
            batch_op.alter_column('created_at',
                                existing_type=sa.DateTime(timezone=True),
                                type_=sa.DateTime(),
                                existing_nullable=True)
        if get_column_type(connection, 'scripts', 'updated_at') == 'DATETIME WITH TIME ZONE':
            batch_op.alter_column('updated_at',
                                existing_type=sa.DateTime(timezone=True),
                                type_=sa.DateTime(),
                                existing_nullable=True)
    
    with op.batch_alter_table('executions', schema=None) as batch_op:
        if get_column_type(connection, 'executions', 'started_at') == 'DATETIME WITH TIME ZONE':
            batch_op.alter_column('started_at',
                                existing_type=sa.DateTime(timezone=True),
                                type_=sa.DateTime(),
                                existing_nullable=True)
        if get_column_type(connection, 'executions', 'completed_at') == 'DATETIME WITH TIME ZONE':
            batch_op.alter_column('completed_at',
                                existing_type=sa.DateTime(timezone=True),
                                type_=sa.DateTime(),
                                existing_nullable=True)
    
    with op.batch_alter_table('schedules', schema=None) as batch_op:
        if get_column_type(connection, 'schedules', 'created_at') == 'DATETIME WITH TIME ZONE':
            batch_op.alter_column('created_at',
                                existing_type=sa.DateTime(timezone=True),
                                type_=sa.DateTime(),
                                existing_nullable=True) 