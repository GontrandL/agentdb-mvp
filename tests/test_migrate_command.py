import json
import os
from pathlib import Path

import sqlite3
from click.testing import CliRunner

from agentdb import core


def create_legacy_db(tmp_path: Path):
    db_path = tmp_path / ".agentdb" / "agent.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at DATETIME,
            checksum TEXT,
            description TEXT
        );
        INSERT INTO schema_migrations(version, applied_at, checksum, description)
        VALUES ('001_initial_schema', datetime('now'), 'abc', 'legacy');
        """
    )
    conn.commit()
    conn.close()
    return db_path


def test_migrate_upgrades_legacy_schema(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    create_legacy_db(tmp_path)

    runner = CliRunner()
    result = runner.invoke(core.cli, ["migrate"])  # type: ignore[attr-defined]
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.splitlines()[-1])
    assert payload["ok"] is True
    assert payload["from_version"] == 0
    assert payload["to_version"] >= 1
    assert "v0_to_v1" in payload["migrations_applied"]

    conn = sqlite3.connect(tmp_path / ".agentdb" / "agent.sqlite")
    row = conn.execute("SELECT version FROM db_version").fetchone()
    assert row[0] >= 1
    conn.close()


def test_migrate_no_db(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(core.cli, ["migrate"])  # type: ignore[attr-defined]
    assert result.exit_code == 2
    payload = json.loads(result.output.strip())
    assert payload["error"] == "no_db_found"


def test_migrate_dry_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    create_legacy_db(tmp_path)
    runner = CliRunner()
    result = runner.invoke(core.cli, ["migrate", "--dry-run"])  # type: ignore[attr-defined]
    assert result.exit_code == 0
    payload = json.loads(result.output.splitlines()[-1])
    assert payload["dry_run"] is True
    assert payload["backup"] is None

AGTAG_METADATA = """

<!--AGTAG v1 START-->
{
  "version": "v1",
  "symbols": [
    {
      "name": "create_legacy_db",
      "kind": "function",
      "qualified_name": "tests.test_migrate_command.create_legacy_db",
      "lines": [
        11,
        29
      ],
      "summary_l0": "Helper function create_legacy_db supporting test utilities.",
      "contract_l1": "def create_legacy_db(tmp_path: Path)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_migrate_command.py"
    },
    {
      "name": "test_migrate_upgrades_legacy_schema",
      "kind": "function",
      "qualified_name": "tests.test_migrate_command.test_migrate_upgrades_legacy_schema",
      "lines": [
        32,
        48
      ],
      "summary_l0": "Pytest case test_migrate_upgrades_legacy_schema validating expected behaviour.",
      "contract_l1": "def test_migrate_upgrades_legacy_schema(tmp_path, monkeypatch)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_migrate_command.py"
    },
    {
      "name": "test_migrate_no_db",
      "kind": "function",
      "qualified_name": "tests.test_migrate_command.test_migrate_no_db",
      "lines": [
        51,
        57
      ],
      "summary_l0": "Pytest case test_migrate_no_db validating expected behaviour.",
      "contract_l1": "def test_migrate_no_db(tmp_path, monkeypatch)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_migrate_command.py"
    },
    {
      "name": "test_migrate_dry_run",
      "kind": "function",
      "qualified_name": "tests.test_migrate_command.test_migrate_dry_run",
      "lines": [
        60,
        68
      ],
      "summary_l0": "Pytest case test_migrate_dry_run validating expected behaviour.",
      "contract_l1": "def test_migrate_dry_run(tmp_path, monkeypatch)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_migrate_command.py"
    }
  ],
  "tests": [
    {
      "path": "tests/test_migrate_command.py",
      "name": "tests.test_migrate_command.test_migrate_upgrades_legacy_schema",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_migrate_command.py",
      "name": "tests.test_migrate_command.test_migrate_no_db",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_migrate_command.py",
      "name": "tests.test_migrate_command.test_migrate_dry_run",
      "covers": [],
      "status": "new"
    }
  ]
}
<!--AGTAG v1 END-->
"""
