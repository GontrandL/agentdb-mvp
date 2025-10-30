import json
import os
from pathlib import Path

from click.testing import CliRunner

from agentdb import core


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_directory_ingest_basic(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # Sample files
    write_file(tmp_path / "notes" / "guide.md", "# Overview\n\nContent line\n")
    write_file(tmp_path / "notes" / "skip.txt", "skip")
    write_file(tmp_path / "node_modules" / "pkg.md", "# Should be excluded\n")

    runner = CliRunner()
    result = runner.invoke(
        core.cli,
        [
            "ingest",
            "--directory",
            str(tmp_path / "notes"),
            "--pattern",
            "*.md",
            "--exclude",
            "node_modules/*",
            "--auto-tag",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.splitlines()[-1])
    assert payload["ok"] is True
    assert payload["files_ingested"] == 1
    assert payload["results"][0]["path"].endswith("notes/guide.md")

    # Validate database contents
    conn = core.ensure_db()
    try:
        row = conn.execute(
            "SELECT repo_path FROM files WHERE repo_path=?",
            ("notes/guide.md",),
        ).fetchone()
        assert row is not None
    finally:
        conn.close()


def test_directory_ingest_auto_tag(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    content = "# Title\n\nParagraph\n- step one\n- step two\n"
    src_path = tmp_path / "docs" / "memo.md"
    write_file(src_path, content)

    runner = CliRunner()
    result = runner.invoke(
        core.cli,
        [
            "ingest",
            "--directory",
            str(tmp_path / "docs"),
            "--auto-tag",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.splitlines()[-1])
    assert payload["ok"] is True
    # Auto-tag writes back to file; ensure AGTAG block exists
    text = src_path.read_text(encoding="utf-8")
    assert "<!--AGTAG v1 START-->" in text

AGTAG_METADATA = """

<!--AGTAG v1 START-->
{
  "version": "v1",
  "symbols": [
    {
      "name": "write_file",
      "kind": "function",
      "qualified_name": "tests.test_directory_ingest.write_file",
      "lines": [
        10,
        12
      ],
      "summary_l0": "Helper function write_file supporting test utilities.",
      "contract_l1": "def write_file(path: Path, content: str) -> None",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_directory_ingest.py"
    },
    {
      "name": "test_directory_ingest_basic",
      "kind": "function",
      "qualified_name": "tests.test_directory_ingest.test_directory_ingest_basic",
      "lines": [
        15,
        52
      ],
      "summary_l0": "Pytest case test_directory_ingest_basic validating expected behaviour.",
      "contract_l1": "def test_directory_ingest_basic(tmp_path, monkeypatch)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_directory_ingest.py"
    },
    {
      "name": "test_directory_ingest_auto_tag",
      "kind": "function",
      "qualified_name": "tests.test_directory_ingest.test_directory_ingest_auto_tag",
      "lines": [
        55,
        76
      ],
      "summary_l0": "Pytest case test_directory_ingest_auto_tag validating expected behaviour.",
      "contract_l1": "def test_directory_ingest_auto_tag(tmp_path, monkeypatch)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_directory_ingest.py"
    }
  ],
  "tests": [
    {
      "path": "tests/test_directory_ingest.py",
      "name": "tests.test_directory_ingest.test_directory_ingest_basic",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_directory_ingest.py",
      "name": "tests.test_directory_ingest.test_directory_ingest_auto_tag",
      "covers": [],
      "status": "new"
    }
  ]
}
<!--AGTAG v1 END-->
"""
