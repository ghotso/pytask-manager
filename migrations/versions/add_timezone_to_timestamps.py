"""Add timezone support to timestamp columns

Revision ID: add_timezone_to_timestamps
Revises: remove_schedule_is_active
Create Date: 2024-02-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_timezone_to_timestamps'
down_revision: Union[str, None] = 'remove_schedule_is_active'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Disable foreign key checks temporarily
    op.execute('PRAGMA foreign_keys=OFF')
    
    try:
        # Step 1: Drop all tables in reverse order of dependencies
        op.execute('DROP TABLE IF EXISTS script_tags')
        op.execute('DROP TABLE IF EXISTS executions')
        op.execute('DROP TABLE IF EXISTS schedules')
        op.execute('DROP TABLE IF EXISTS dependencies')
        op.execute('DROP TABLE IF EXISTS scripts')
        
        # Step 2: Create tables in correct order with proper foreign key constraints
        op.execute('''
            CREATE TABLE scripts (
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
            CREATE TABLE schedules (
                id INTEGER NOT NULL PRIMARY KEY,
                script_id INTEGER NOT NULL,
                cron_expression VARCHAR(100) NOT NULL,
                description VARCHAR(255),
                created_at DATETIME NOT NULL,
                FOREIGN KEY(script_id) REFERENCES scripts(id) ON DELETE CASCADE
            )
        ''')
        
        op.execute('''
            CREATE TABLE executions (
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
            CREATE TABLE dependencies (
                id INTEGER NOT NULL PRIMARY KEY,
                script_id INTEGER NOT NULL,
                package_name VARCHAR(255) NOT NULL,
                version_spec VARCHAR(100) NOT NULL,
                installed_version VARCHAR(100),
                FOREIGN KEY(script_id) REFERENCES scripts(id) ON DELETE CASCADE
            )
        ''')
        
        op.execute('''
            CREATE TABLE script_tags (
                script_id INTEGER,
                tag_id INTEGER,
                FOREIGN KEY(script_id) REFERENCES scripts(id) ON DELETE CASCADE,
                FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
        ''')
        
    finally:
        # Re-enable foreign key checks
        op.execute('PRAGMA foreign_keys=ON')


def downgrade() -> None:
    # Disable foreign key checks temporarily
    op.execute('PRAGMA foreign_keys=OFF')
    
    try:
        # Step 1: Drop all tables in reverse order
        op.execute('DROP TABLE IF EXISTS script_tags')
        op.execute('DROP TABLE IF EXISTS executions')
        op.execute('DROP TABLE IF EXISTS schedules')
        op.execute('DROP TABLE IF EXISTS dependencies')
        op.execute('DROP TABLE IF EXISTS scripts')
        
        # Step 2: Recreate tables without timezone support
        op.execute('''
            CREATE TABLE scripts (
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
            CREATE TABLE schedules (
                id INTEGER NOT NULL PRIMARY KEY,
                script_id INTEGER NOT NULL,
                cron_expression VARCHAR(100) NOT NULL,
                description VARCHAR(255),
                created_at DATETIME NOT NULL,
                FOREIGN KEY(script_id) REFERENCES scripts(id)
            )
        ''')
        
        op.execute('''
            CREATE TABLE executions (
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
            CREATE TABLE dependencies (
                id INTEGER NOT NULL PRIMARY KEY,
                script_id INTEGER NOT NULL,
                package_name VARCHAR(255) NOT NULL,
                version_spec VARCHAR(100) NOT NULL,
                installed_version VARCHAR(100),
                FOREIGN KEY(script_id) REFERENCES scripts(id)
            )
        ''')
        
        op.execute('''
            CREATE TABLE script_tags (
                script_id INTEGER,
                tag_id INTEGER,
                FOREIGN KEY(script_id) REFERENCES scripts(id),
                FOREIGN KEY(tag_id) REFERENCES tags(id)
            )
        ''')
        
    finally:
        # Re-enable foreign key checks
        op.execute('PRAGMA foreign_keys=ON') 