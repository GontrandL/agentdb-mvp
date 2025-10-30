"""Performance index for symbol lookups."""

import sqlite3

DESCRIPTION = "Add composite index for symbols(repo_path, name)"
CHECKSUM = "sha256:1c10bbb1178e0a55f581330761af96902d37e0e4586f0c6e4e9f2e529c3ca50f"


def up(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_symbols_lookup
        ON symbols(repo_path, name);
        """
    )


def down(conn: sqlite3.Connection) -> None:
    conn.execute("DROP INDEX IF EXISTS idx_symbols_lookup")


