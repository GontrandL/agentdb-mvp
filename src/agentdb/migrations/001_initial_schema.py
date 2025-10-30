"""Initial AgentDB schema."""

import sqlite3
from pathlib import Path

DESCRIPTION = "Initial schema with files, symbols, edges, FTS"
CHECKSUM = "sha256:6b44f8f1c3253f3d90640eb1253857a139ed6ed78e878dec577249c9251b44ed"

SCHEMA_FILE = Path(__file__).resolve().parents[3] / "schema.sql"


def up(conn: sqlite3.Connection) -> None:
    text = SCHEMA_FILE.read_text(encoding="utf-8")
    conn.executescript(text)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS db_version (
            version INTEGER PRIMARY KEY,
            upgraded_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute("INSERT OR IGNORE INTO db_version (version) VALUES (1)")


def down(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS symbols_fts;
        DROP TABLE IF EXISTS ops_log;
        DROP TABLE IF EXISTS edges;
        DROP TABLE IF EXISTS symbols;
        DROP TABLE IF EXISTS files;
        DROP TABLE IF EXISTS db_version;
        """
    )


