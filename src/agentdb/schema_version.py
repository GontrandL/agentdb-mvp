"""Utility helpers for managing AgentDB schema versions."""

from __future__ import annotations

import sqlite3
from typing import Tuple

CURRENT_DB_VERSION = 1


def ensure_version_table(conn: sqlite3.Connection) -> None:
    """Ensure the db_version tracking table exists."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS db_version (
            version INTEGER PRIMARY KEY,
            upgraded_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def record_version(conn: sqlite3.Connection, version: int) -> None:
    """Persist the current schema version."""
    ensure_version_table(conn)
    conn.execute(
        "INSERT OR REPLACE INTO db_version (rowid, version) VALUES (1, ?)",
        (version,),
    )
    conn.commit()


def get_version(conn: sqlite3.Connection) -> Tuple[int, bool]:
    """Return current version, creating table if missing."""
    ensure_version_table(conn)
    row = conn.execute("SELECT version FROM db_version LIMIT 1").fetchone()
    if not row:
        conn.execute("INSERT OR REPLACE INTO db_version (rowid, version) VALUES (1, ?)", (CURRENT_DB_VERSION,))
        conn.commit()
        return CURRENT_DB_VERSION, True
    return int(row[0]), False


