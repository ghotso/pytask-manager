"""Add cascade delete to foreign keys

Revision ID: add_cascade_delete_to_foreign_keys
Revises: add_timezone_to_timestamps
Create Date: 2024-02-07 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_cascade_delete_to_foreign_keys'
down_revision: Union[str, None] = 'add_timezone_to_timestamps'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop any leftover temporary tables from failed migrations
    op.execute('DROP TABLE IF EXISTS _alembic_tmp_dependencies')
    op.execute('DROP TABLE IF EXISTS _alembic_tmp_executions')
    op.execute('DROP TABLE IF EXISTS _alembic_tmp_schedules')
    
    # Dependencies table
    op.execute('''
        CREATE TABLE _alembic_tmp_dependencies (
            id INTEGER NOT NULL PRIMARY KEY,
            script_id INTEGER NOT NULL,
            package_name VARCHAR(255) NOT NULL,
            version_spec VARCHAR(100) NOT NULL,
            installed_version VARCHAR(100),
            FOREIGN KEY(script_id) REFERENCES scripts(id) ON DELETE CASCADE
        )
    ''')
    op.execute('INSERT INTO _alembic_tmp_dependencies SELECT * FROM dependencies')
    op.execute('DROP TABLE dependencies')
    op.execute('ALTER TABLE _alembic_tmp_dependencies RENAME TO dependencies')
    
    # Executions table
    op.execute('''
        CREATE TABLE _alembic_tmp_executions (
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
    op.execute('INSERT INTO _alembic_tmp_executions SELECT * FROM executions')
    op.execute('DROP TABLE executions')
    op.execute('ALTER TABLE _alembic_tmp_executions RENAME TO executions')
    
    # Schedules table
    op.execute('''
        CREATE TABLE _alembic_tmp_schedules (
            id INTEGER NOT NULL PRIMARY KEY,
            script_id INTEGER NOT NULL,
            cron_expression VARCHAR(100) NOT NULL,
            description VARCHAR(255),
            created_at DATETIME NOT NULL,
            FOREIGN KEY(script_id) REFERENCES scripts(id) ON DELETE CASCADE
        )
    ''')
    op.execute('INSERT INTO _alembic_tmp_schedules SELECT * FROM schedules')
    op.execute('DROP TABLE schedules')
    op.execute('ALTER TABLE _alembic_tmp_schedules RENAME TO schedules')


def downgrade() -> None:
    # Drop any leftover temporary tables
    op.execute('DROP TABLE IF EXISTS _alembic_tmp_dependencies')
    op.execute('DROP TABLE IF EXISTS _alembic_tmp_executions')
    op.execute('DROP TABLE IF EXISTS _alembic_tmp_schedules')
    
    # Dependencies table
    op.execute('''
        CREATE TABLE _alembic_tmp_dependencies (
            id INTEGER NOT NULL PRIMARY KEY,
            script_id INTEGER NOT NULL,
            package_name VARCHAR(255) NOT NULL,
            version_spec VARCHAR(100) NOT NULL,
            installed_version VARCHAR(100),
            FOREIGN KEY(script_id) REFERENCES scripts(id)
        )
    ''')
    op.execute('INSERT INTO _alembic_tmp_dependencies SELECT * FROM dependencies')
    op.execute('DROP TABLE dependencies')
    op.execute('ALTER TABLE _alembic_tmp_dependencies RENAME TO dependencies')
    
    # Executions table
    op.execute('''
        CREATE TABLE _alembic_tmp_executions (
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
    op.execute('INSERT INTO _alembic_tmp_executions SELECT * FROM executions')
    op.execute('DROP TABLE executions')
    op.execute('ALTER TABLE _alembic_tmp_executions RENAME TO executions')
    
    # Schedules table
    op.execute('''
        CREATE TABLE _alembic_tmp_schedules (
            id INTEGER NOT NULL PRIMARY KEY,
            script_id INTEGER NOT NULL,
            cron_expression VARCHAR(100) NOT NULL,
            description VARCHAR(255),
            created_at DATETIME NOT NULL,
            FOREIGN KEY(script_id) REFERENCES scripts(id)
        )
    ''')
    op.execute('INSERT INTO _alembic_tmp_schedules SELECT * FROM schedules')
    op.execute('DROP TABLE schedules')
    op.execute('ALTER TABLE _alembic_tmp_schedules RENAME TO schedules') 