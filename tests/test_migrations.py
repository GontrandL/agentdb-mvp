import os
from pathlib import Path

import sqlite3

from agentdb.core import ensure_db, DB_FILE


def _schema_versions(conn: sqlite3.Connection):
    return [
        row[0]
        for row in conn.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
    ]


def _expected_versions() -> list[str]:
    dashboard_dir = Path(__file__).resolve().parents[1] / "dashboard" / "db" / "migrations"
    agentdb_dir = Path(__file__).resolve().parents[1] / "src" / "agentdb" / "migrations"
    versions = {
        path.stem
        for path in dashboard_dir.glob("*")
        if path.suffix in {".sql", ".py"}
    }
    versions.update(
        path.stem
        for path in agentdb_dir.glob("[0-9][0-9][0-9]_*.py")
    )
    return sorted(versions)


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return bool(row)


def test_migrations_apply_all_versions(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    conn = ensure_db()
    try:
        versions = _schema_versions(conn)
        assert versions == _expected_versions()
        # spot check newly added tables by migrations
        for table in [
            "documents_multilevel",
            "documents_files",
            "documents_fts",
            "webhooks",
            "webhook_logs",
        ]:
            assert _table_exists(conn, table), f"Expected table missing: {table}"
    finally:
        conn.close()

    # Second run should be idempotent
    conn = ensure_db()
    try:
        versions_again = _schema_versions(conn)
        assert versions_again == _expected_versions()
    finally:
        conn.close()

    # Ensure DB file created inside working directory
    assert (tmp_path / DB_FILE).exists()

AGTAG_METADATA = """

<!--AGTAG v1 START-->
{
  "version": "v1",
  "symbols": [
    {
      "name": "_schema_versions",
      "kind": "function",
      "qualified_name": "tests.test_migrations._schema_versions",
      "lines": [
        9,
        15
      ],
      "summary_l0": "Helper function _schema_versions supporting test utilities.",
      "contract_l1": "def _schema_versions(conn: sqlite3.Connection)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_migrations.py"
    },
    {
      "name": "_expected_versions",
      "kind": "function",
      "qualified_name": "tests.test_migrations._expected_versions",
      "lines": [
        18,
        30
      ],
      "summary_l0": "Helper function _expected_versions supporting test utilities.",
      "contract_l1": "def _expected_versions() -> list[str]",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_migrations.py"
    },
    {
      "name": "_table_exists",
      "kind": "function",
      "qualified_name": "tests.test_migrations._table_exists",
      "lines": [
        33,
        38
      ],
      "summary_l0": "Helper function _table_exists supporting test utilities.",
      "contract_l1": "def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_migrations.py"
    },
    {
      "name": "test_migrations_apply_all_versions",
      "kind": "function",
      "qualified_name": "tests.test_migrations.test_migrations_apply_all_versions",
      "lines": [
        41,
        69
      ],
      "summary_l0": "Pytest case test_migrations_apply_all_versions validating expected behaviour.",
      "contract_l1": "def test_migrations_apply_all_versions(tmp_path, monkeypatch)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_migrations.py"
    }
  ],
  "tests": [
    {
      "path": "tests/test_migrations.py",
      "name": "tests.test_migrations.test_migrations_apply_all_versions",
      "covers": [],
      "status": "new"
    }
  ]
}
<!--AGTAG v1 END-->
"""
