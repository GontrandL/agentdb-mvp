import json
import sqlite3
from click.testing import CliRunner

from agentdb import core


def test_init_handles_operational_error(monkeypatch):
    runner = CliRunner()

    def fail_init():
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(core, "ensure_db", fail_init)
    result = runner.invoke(core.cli, ["init"])
    assert result.exit_code == 2
    payload = json.loads(result.output.strip())
    assert payload["error"] == "init_failed"
    assert "disk I/O error" in payload["hint"]


def test_focus_handles_db_error(monkeypatch):
    runner = CliRunner()

    def fail_db():
        raise sqlite3.OperationalError("cannot open database file")

    monkeypatch.setattr(core, "ensure_db", fail_db)
    result = runner.invoke(
        core.cli,
        ["focus", "--handle", "ctx://src/foo.py::bar@sha256:ANY", "--depth", "1"],
    )
    assert result.exit_code == 2
    payload = json.loads(result.output.strip())
    assert payload["error"] == "db_unavailable"
    assert "cannot open database file" in payload["hint"]

AGTAG_METADATA = """

<!--AGTAG v1 START-->
{
  "version": "v1",
  "symbols": [
    {
      "name": "test_init_handles_operational_error",
      "kind": "function",
      "qualified_name": "tests.test_cli_errors.test_init_handles_operational_error",
      "lines": [
        8,
        19
      ],
      "summary_l0": "Pytest case test_init_handles_operational_error validating expected behaviour.",
      "contract_l1": "def test_init_handles_operational_error(monkeypatch)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_cli_errors.py"
    },
    {
      "name": "test_focus_handles_db_error",
      "kind": "function",
      "qualified_name": "tests.test_cli_errors.test_focus_handles_db_error",
      "lines": [
        22,
        36
      ],
      "summary_l0": "Pytest case test_focus_handles_db_error validating expected behaviour.",
      "contract_l1": "def test_focus_handles_db_error(monkeypatch)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_cli_errors.py"
    }
  ],
  "tests": [
    {
      "path": "tests/test_cli_errors.py",
      "name": "tests.test_cli_errors.test_init_handles_operational_error",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_cli_errors.py",
      "name": "tests.test_cli_errors.test_focus_handles_db_error",
      "covers": [],
      "status": "new"
    }
  ]
}
<!--AGTAG v1 END-->
"""
