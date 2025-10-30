"""Database migration tooling for AgentDB."""

from __future__ import annotations

import hashlib
import importlib.util
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

LOGGER = logging.getLogger(__name__)

SCHEMA_MIGRATIONS_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    checksum TEXT,
    description TEXT
);
"""


@dataclass
class Migration:
    """Database migration metadata."""
    version: str
    description: str
    checksum: str
    sql: str


class MigrationRunner:
    """Runs database migrations in order."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._ensure_migrations_table()

    def _ensure_migrations_table(self):
        """Create schema_migrations table if it doesn't exist."""
        self.conn.executescript(SCHEMA_MIGRATIONS_SQL)
        self.conn.commit()

    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions."""
        cursor = self.conn.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        )
        return [row[0] for row in cursor.fetchall()]

    def get_pending_migrations(self) -> List[Migration]:
        """Get list of pending migrations to apply."""
        # For MVP, return empty list - migrations are applied manually via CLI
        return []

    def apply_migration(self, migration: Migration):
        """Apply a single migration."""
        LOGGER.info(f"Applying migration {migration.version}: {migration.description}")

        # Execute migration SQL
        self.conn.executescript(migration.sql)

        # Record migration
        self.conn.execute(
            "INSERT INTO schema_migrations (version, checksum, description) VALUES (?, ?, ?)",
            (migration.version, migration.checksum, migration.description)
        )
        self.conn.commit()

        LOGGER.info(f"Migration {migration.version} applied successfully")
