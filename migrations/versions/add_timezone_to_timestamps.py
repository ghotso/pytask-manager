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
    
    # Create temporary tables with timezone support
    op.execute('''
        CREATE TABLE scripts_new (
            id INTEGER NOT NULL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            description VARCHAR(1000),
            content VARCHAR NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            is_active BOOLEAN NOT NULL
        )
    ''')
    
    op.execute('''
        CREATE TABLE executions_new (
            id INTEGER NOT NULL PRIMARY KEY,
            script_id INTEGER NOT NULL,
            schedule_id INTEGER,
            started_at DATETIME NOT NULL,
            completed_at DATETIME,
            status VARCHAR NOT NULL,
            log_output VARCHAR,
            error_message VARCHAR,
            FOREIGN KEY(script_id) REFERENCES scripts(id) ON DELETE CASCADE,
            FOREIGN KEY(schedule_id) REFERENCES schedules(id) ON DELETE SET NULL
        )
    ''')
    
    op.execute('''
        CREATE TABLE schedules_new (
            id INTEGER NOT NULL PRIMARY KEY,
            script_id INTEGER NOT NULL,
            cron_expression VARCHAR(100) NOT NULL,
            description VARCHAR(255),
            created_at DATETIME NOT NULL,
            FOREIGN KEY(script_id) REFERENCES scripts(id) ON DELETE CASCADE
        )
    ''')
    
    # Copy data to new tables
    op.execute('INSERT INTO scripts_new SELECT * FROM scripts')
    op.execute('INSERT INTO executions_new SELECT * FROM executions')
    op.execute('INSERT INTO schedules_new SELECT * FROM schedules')
    
    # Drop old tables and rename new ones
    op.execute('DROP TABLE executions')
    op.execute('DROP TABLE schedules')
    op.execute('DROP TABLE scripts')
    
    op.execute('ALTER TABLE scripts_new RENAME TO scripts')
    op.execute('ALTER TABLE executions_new RENAME TO executions')
    op.execute('ALTER TABLE schedules_new RENAME TO schedules')


def downgrade() -> None:
    # Similar process but removing timezone support
    connection = op.get_bind()
    
    op.execute('''
        CREATE TABLE scripts_old (
            id INTEGER NOT NULL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            description VARCHAR(1000),
            content VARCHAR NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            is_active BOOLEAN NOT NULL
        )
    ''')
    
    op.execute('''
        CREATE TABLE executions_old (
            id INTEGER NOT NULL PRIMARY KEY,
            script_id INTEGER NOT NULL,
            schedule_id INTEGER,
            started_at DATETIME NOT NULL,
            completed_at DATETIME,
            status VARCHAR NOT NULL,
            log_output VARCHAR,
            error_message VARCHAR,
            FOREIGN KEY(script_id) REFERENCES scripts(id),
            FOREIGN KEY(schedule_id) REFERENCES schedules(id)
        )
    ''')
    
    op.execute('''
        CREATE TABLE schedules_old (
            id INTEGER NOT NULL PRIMARY KEY,
            script_id INTEGER NOT NULL,
            cron_expression VARCHAR(100) NOT NULL,
            description VARCHAR(255),
            created_at DATETIME NOT NULL,
            FOREIGN KEY(script_id) REFERENCES scripts(id)
        )
    ''')
    
    # Copy data to old tables
    op.execute('INSERT INTO scripts_old SELECT * FROM scripts')
    op.execute('INSERT INTO executions_old SELECT * FROM executions')
    op.execute('INSERT INTO schedules_old SELECT * FROM schedules')
    
    # Drop new tables and rename old ones
    op.execute('DROP TABLE executions')
    op.execute('DROP TABLE schedules')
    op.execute('DROP TABLE scripts')
    
    op.execute('ALTER TABLE scripts_old RENAME TO scripts')
    op.execute('ALTER TABLE executions_old RENAME TO executions')
    op.execute('ALTER TABLE schedules_old RENAME TO schedules') 