import json, os, sqlite3, subprocess, sys, pathlib

EXAMPLE_CODE = "def example(a,b):\n    return a+b\n"
EXAMPLE_AGTAG = """
<!--AGTAG v1 START-->
{"version":"v1","symbols":[{"path":"src/example.py","name":"example","kind":"function","lines":[1,2],"summary_l0":"adds two numbers","contract_l1":"@io a:int,b:int -> int"}]}
<!--AGTAG v1 END-->
"""

FOCUS_CODE = (
    "def helper():\n"
    "    return 42\n"
    "\n"
    "\n"
    "def main():\n"
    "    value = helper()\n"
    "    return value * 2\n"
)

FOCUS_AGTAG = """
<!--AGTAG v1 START-->
{"version":"v1","symbols":[
  {"path":"src/focus_demo.py","name":"helper","kind":"function","lines":[1,2],"summary_l0":"returns 42","contract_l1":"@io -> int"},
  {"path":"src/focus_demo.py","name":"main","kind":"function","lines":[5,7],"summary_l0":"calls helper","contract_l1":"@io -> int"}
]}
<!--AGTAG v1 END-->
"""

def run_cmd(args, stdin_text=None):
    cmd = [sys.executable, "-m", "agentdb.core"] + args
    env = os.environ.copy()
    repo_root = pathlib.Path(__file__).parent.parent
    src_path = str(repo_root / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src_path if not existing else f"{src_path}:{existing}"
    p = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE if stdin_text else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    out, err = p.communicate(stdin_text)
    return p.returncode, out, err

def prepare_repo(tmp_path, monkeypatch):
    repo_root = pathlib.Path(__file__).parent.parent
    monkeypatch.syspath_prepend(str(repo_root / "src"))
    os.chdir(tmp_path)
    rc, out, err = run_cmd(["init"])
    assert rc == 0, (rc, out, err)

def ingest_example_file():
    full = EXAMPLE_CODE + "\n" + EXAMPLE_AGTAG
    rc, out, err = run_cmd(["ingest","--path","src/example.py"], stdin_text=full)
    return rc, out, err

def parse_cli_json(out, err):
    payload = out.strip() or err.strip()
    return json.loads(payload)


def ingest_focus_demo(tmp_path, monkeypatch):
    prepare_repo(tmp_path, monkeypatch)
    full = FOCUS_CODE + "\n" + FOCUS_AGTAG
    rc, out, err = run_cmd(["ingest", "--path", "src/focus_demo.py"], stdin_text=full)
    assert rc == 0, (rc, out, err)
    return json.loads(out)

def test_ingest_and_focus(tmp_path, monkeypatch):
    prepare_repo(tmp_path, monkeypatch)
    rc, out, err = ingest_example_file()
    assert rc == 0, (rc,out,err)
    payload = json.loads(out)
    assert payload.get("ok") is True
    # focus
    rc, out, err = run_cmd(["focus","--handle","ctx://src/example.py::example@sha256:ANY","--depth","1"])
    assert rc == 0
    data = json.loads(out)
    assert data["primary"]["name"] == "example"
    assert data["neighbors"] == {}
    assert data["edges"] == []


def test_patch_replaces_symbols(tmp_path, monkeypatch):
    prepare_repo(tmp_path, monkeypatch)
    rc, out, err = ingest_example_file()
    assert rc == 0
    payload = json.loads(out)
    original_hash = payload["file_hash"]

    new_code = "def example(a,b):\n    return a-b\n"
    new_agtag = """
<!--AGTAG v1 START-->
{"version":"v1","symbols":[{"path":"src/example.py","name":"example","kind":"function","lines":[1,2],"summary_l0":"subtracts two numbers","contract_l1":"@io a:int,b:int -> int"}]}
<!--AGTAG v1 END-->
"""
    final_file = (new_code + "\n" + new_agtag).rstrip("\n") + "\n"
    patch_payload = json.dumps({"final_file": final_file})
    diff = (
        "--- a/src/example.py\n"
        "+++ b/src/example.py\n"
        "@@ -1,2 +1,2 @@\n"
        "-def example(a,b):\n"
        "-    return a+b\n"
        "+def example(a,b):\n"
        "+    return a-b\n"
        "@@ -6,1 +6,1 @@\n"
        "-{\"version\":\"v1\",\"symbols\":[{\"path\":\"src/example.py\",\"name\":\"example\",\"kind\":\"function\",\"lines\":[1,2],\"summary_l0\":\"adds two numbers\",\"contract_l1\":\"@io a:int,b:int -> int\"}]}\n"
        "+{\"version\":\"v1\",\"symbols\":[{\"path\":\"src/example.py\",\"name\":\"example\",\"kind\":\"function\",\"lines\":[1,2],\"summary_l0\":\"subtracts two numbers\",\"contract_l1\":\"@io a:int,b:int -> int\"}]}\n"
        "AGTAG_PATCH_FINAL_FILE\n"
        f"{patch_payload}\n"
        "END\n"
    )

    rc, out, err = run_cmd(
        ["patch", "--path", "src/example.py", "--hash-before", original_hash],
        stdin_text=diff
    )
    assert rc == 0, err
    result = json.loads(out)
    assert result.get("ok") is True

    conn = sqlite3.connect(".agentdb/agent.sqlite")
    try:
        symbol_count = conn.execute(
            "SELECT COUNT(*) FROM symbols WHERE repo_path=?", ("src/example.py",)
        ).fetchone()[0]
        assert symbol_count == 1

        overview = conn.execute(
            "SELECT l0_overview FROM symbols WHERE repo_path=?", ("src/example.py",)
        ).fetchone()[0]
        assert overview == "subtracts two numbers"

        fts_count = conn.execute(
            "SELECT COUNT(*) FROM symbols_fts WHERE repo_path=?", ("src/example.py",)
        ).fetchone()[0]
        assert fts_count == 1
    finally:
        conn.close()


def test_ingest_rejects_invalid_agtag(tmp_path, monkeypatch):
    prepare_repo(tmp_path, monkeypatch)
    invalid_agtag = """
<!--AGTAG v1 START-->
{"version":"v2","symbols":[{"path":"src/example.py","name":"example","kind":"function","lines":[1,2]}]}
<!--AGTAG v1 END-->
"""
    full = EXAMPLE_CODE + "\n" + invalid_agtag
    rc, out, err = run_cmd(["ingest","--path","src/example.py"], stdin_text=full)
    assert rc == 2
    payload = parse_cli_json(out, err)
    assert payload["error"] == "agtag_invalid"


def test_ingest_rejects_unsafe_path(tmp_path, monkeypatch):
    prepare_repo(tmp_path, monkeypatch)
    full = EXAMPLE_CODE + "\n" + EXAMPLE_AGTAG
    rc, out, err = run_cmd(["ingest","--path","../outside.py"], stdin_text=full)
    assert rc == 2
    payload = parse_cli_json(out, err)
    assert payload["error"] == "unsafe_path"


def test_patch_without_final_payload(tmp_path, monkeypatch):
    prepare_repo(tmp_path, monkeypatch)
    rc, out, err = ingest_example_file()
    assert rc == 0
    original_hash = json.loads(out)["file_hash"]

    new_code = "def example(a,b):\n    return a-b\n"
    diff = (
        "--- a/src/example.py\n"
        "+++ b/src/example.py\n"
        "@@ -1,2 +1,2 @@\n"
        "-def example(a,b):\n"
        "-    return a+b\n"
        "+def example(a,b):\n"
        "+    return a-b\n"
    )
    rc, out, err = run_cmd(
        ["patch", "--path", "src/example.py", "--hash-before", original_hash],
        stdin_text=diff
    )
    assert rc == 0, err
    result = json.loads(out)
    assert result["ok"] is True


def test_patch_rejects_final_file_mismatch(tmp_path, monkeypatch):
    prepare_repo(tmp_path, monkeypatch)
    rc, out, err = ingest_example_file()
    assert rc == 0
    original_hash = json.loads(out)["file_hash"]

    new_code = "def example(a,b):\n    return a-b\n"
    new_agtag = """
<!--AGTAG v1 START-->
{"version":"v1","symbols":[{"path":"src/example.py","name":"example","kind":"function","lines":[1,2],"summary_l0":"subtracts two numbers","contract_l1":"@io a:int,b:int -> int"}]}
<!--AGTAG v1 END-->
"""
    final_file = (new_code + "\n" + new_agtag).rstrip("\n") + "\n"
    mismatched_final = final_file.replace("return a-b", "return a+b")
    patch_payload = json.dumps({"final_file": mismatched_final})
    diff = (
        "--- a/src/example.py\n"
        "+++ b/src/example.py\n"
        "@@ -1,2 +1,2 @@\n"
        "-def example(a,b):\n"
        "-    return a+b\n"
        "+def example(a,b):\n"
        "+    return a-b\n"
        "@@ -6,1 +6,1 @@\n"
        "-{\"version\":\"v1\",\"symbols\":[{\"path\":\"src/example.py\",\"name\":\"example\",\"kind\":\"function\",\"lines\":[1,2],\"summary_l0\":\"adds two numbers\",\"contract_l1\":\"@io a:int,b:int -> int\"}]}\n"
        "+{\"version\":\"v1\",\"symbols\":[{\"path\":\"src/example.py\",\"name\":\"example\",\"kind\":\"function\",\"lines\":[1,2],\"summary_l0\":\"subtracts two numbers\",\"contract_l1\":\"@io a:int,b:int -> int\"}]}\n"
        "AGTAG_PATCH_FINAL_FILE\n"
        f"{patch_payload}\n"
        "END\n"
    )
    rc, out, err = run_cmd(
        ["patch", "--path", "src/example.py", "--hash-before", original_hash],
        stdin_text=diff
    )
    assert rc == 2
    payload = parse_cli_json(out, err)
    assert payload["error"] == "final_file_mismatch"


def test_ingest_records_edges(tmp_path, monkeypatch):
    payload = ingest_focus_demo(tmp_path, monkeypatch)
    conn = sqlite3.connect(".agentdb/agent.sqlite")
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT s_src.name AS src, s_dst.name AS dst, e.edge_type
            FROM edges e
            JOIN symbols s_src ON e.src_id = s_src.id
            JOIN symbols s_dst ON e.dst_id = s_dst.id
            WHERE s_src.repo_path = ?
            """,
            ("src/focus_demo.py",),
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) == 1
    assert rows[0]["src"] == "main"
    assert rows[0]["dst"] == "helper"
    assert rows[0]["edge_type"] == "calls"


def test_focus_cli_traversal(tmp_path, monkeypatch):
    payload = ingest_focus_demo(tmp_path, monkeypatch)
    file_hash = payload["file_hash"]
    handle = f"ctx://src/focus_demo.py::main@{file_hash}"

    rc, out, err = run_cmd(["focus", "--handle", handle, "--depth", "0"])
    assert rc == 0, err
    depth_zero = json.loads(out)
    assert depth_zero["primary"]["name"] == "main"
    assert depth_zero["neighbors"] == {}
    assert depth_zero["edges"] == []
    assert depth_zero["stats"]["symbols_returned"] == 1

    rc, out, err = run_cmd(["focus", "--handle", handle, "--depth", "1"])
    assert rc == 0, err
    depth_one = json.loads(out)
    assert depth_one["primary"]["name"] == "main"
    assert "depth_1" in depth_one["neighbors"]
    neighbor_names = {n["name"] for n in depth_one["neighbors"]["depth_1"]}
    assert neighbor_names == {"helper"}
    edge_signatures = {
        (edge["source"]["name"], edge["target"]["name"], edge["type"])
        for edge in depth_one["edges"]
    }
    assert ("main", "helper", "calls") in edge_signatures
    assert depth_one["stats"]["symbols_returned"] == 2
    assert depth_one["stats"]["edges_traversed"] == 1


def test_focus_cli_hash_conflict(tmp_path, monkeypatch):
    payload = ingest_focus_demo(tmp_path, monkeypatch)
    bad_handle = "ctx://src/focus_demo.py::main@sha256:deadbeef"
    rc, out, err = run_cmd(["focus", "--handle", bad_handle, "--depth", "1"])
    assert rc == 2
    error_payload = parse_cli_json(out, err)
    assert error_payload["error"] == "hash_conflict"
    assert error_payload["expected"] == payload["file_hash"]


def test_focus_cli_invalid_handle(tmp_path, monkeypatch):
    prepare_repo(tmp_path, monkeypatch)
    rc, out, err = run_cmd(["focus", "--handle", "not-a-handle", "--depth", "1"])
    assert rc == 2
    error_payload = parse_cli_json(out, err)
    assert error_payload["error"] == "handle_invalid"


def test_inventory_summary(tmp_path, monkeypatch):
    prepare_repo(tmp_path, monkeypatch)
    rc, out, err = ingest_example_file()
    assert rc == 0
    rc, out, err = run_cmd(["inventory", "--summary"])
    assert rc == 0
    lines = [line for line in out.splitlines() if line.strip()]
    assert len(lines) == 2
    entry = json.loads(lines[0])
    summary = json.loads(lines[1])["summary"]
    assert entry["status"] in {"in_sync", "missing_on_disk", "missing_in_db", "stale_on_disk"}
    assert "by_state" in summary
    assert summary["total"] == 1

AGTAG_METADATA = """

<!--AGTAG v1 START-->
{
  "version": "v1",
  "symbols": [
    {
      "name": "run_cmd",
      "kind": "function",
      "qualified_name": "tests.test_ingest_and_focus.run_cmd",
      "lines": [
        29,
        45
      ],
      "summary_l0": "Helper function run_cmd supporting test utilities.",
      "contract_l1": "def run_cmd(args, stdin_text=None)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_ingest_and_focus.py"
    },
    {
      "name": "prepare_repo",
      "kind": "function",
      "qualified_name": "tests.test_ingest_and_focus.prepare_repo",
      "lines": [
        47,
        52
      ],
      "summary_l0": "Helper function prepare_repo supporting test utilities.",
      "contract_l1": "def prepare_repo(tmp_path, monkeypatch)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_ingest_and_focus.py"
    },
    {
      "name": "ingest_example_file",
      "kind": "function",
      "qualified_name": "tests.test_ingest_and_focus.ingest_example_file",
      "lines": [
        54,
        57
      ],
      "summary_l0": "Helper function ingest_example_file supporting test utilities.",
      "contract_l1": "def ingest_example_file()",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_ingest_and_focus.py"
    },
    {
      "name": "parse_cli_json",
      "kind": "function",
      "qualified_name": "tests.test_ingest_and_focus.parse_cli_json",
      "lines": [
        59,
        61
      ],
      "summary_l0": "Helper function parse_cli_json supporting test utilities.",
      "contract_l1": "def parse_cli_json(out, err)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_ingest_and_focus.py"
    },
    {
      "name": "ingest_focus_demo",
      "kind": "function",
      "qualified_name": "tests.test_ingest_and_focus.ingest_focus_demo",
      "lines": [
        64,
        69
      ],
      "summary_l0": "Helper function ingest_focus_demo supporting test utilities.",
      "contract_l1": "def ingest_focus_demo(tmp_path, monkeypatch)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_ingest_and_focus.py"
    },
    {
      "name": "test_ingest_and_focus",
      "kind": "function",
      "qualified_name": "tests.test_ingest_and_focus.test_ingest_and_focus",
      "lines": [
        71,
        83
      ],
      "summary_l0": "Pytest case test_ingest_and_focus validating expected behaviour.",
      "contract_l1": "def test_ingest_and_focus(tmp_path, monkeypatch)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_ingest_and_focus.py"
    },
    {
      "name": "test_patch_replaces_symbols",
      "kind": "function",
      "qualified_name": "tests.test_ingest_and_focus.test_patch_replaces_symbols",
      "lines": [
        86,
        142
      ],
      "summary_l0": "Pytest case test_patch_replaces_symbols validating expected behaviour.",
      "contract_l1": "def test_patch_replaces_symbols(tmp_path, monkeypatch)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_ingest_and_focus.py"
    },
    {
      "name": "test_ingest_rejects_invalid_agtag",
      "kind": "function",
      "qualified_name": "tests.test_ingest_and_focus.test_ingest_rejects_invalid_agtag",
      "lines": [
        145,
        156
      ],
      "summary_l0": "Pytest case test_ingest_rejects_invalid_agtag validating expected behaviour.",
      "contract_l1": "def test_ingest_rejects_invalid_agtag(tmp_path, monkeypatch)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_ingest_and_focus.py"
    },
    {
      "name": "test_ingest_rejects_unsafe_path",
      "kind": "function",
      "qualified_name": "tests.test_ingest_and_focus.test_ingest_rejects_unsafe_path",
      "lines": [
        159,
        165
      ],
      "summary_l0": "Pytest case test_ingest_rejects_unsafe_path validating expected behaviour.",
      "contract_l1": "def test_ingest_rejects_unsafe_path(tmp_path, monkeypatch)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_ingest_and_focus.py"
    },
    {
      "name": "test_patch_without_final_payload",
      "kind": "function",
      "qualified_name": "tests.test_ingest_and_focus.test_patch_without_final_payload",
      "lines": [
        168,
        190
      ],
      "summary_l0": "Pytest case test_patch_without_final_payload validating expected behaviour.",
      "contract_l1": "def test_patch_without_final_payload(tmp_path, monkeypatch)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_ingest_and_focus.py"
    },
    {
      "name": "test_patch_rejects_final_file_mismatch",
      "kind": "function",
      "qualified_name": "tests.test_ingest_and_focus.test_patch_rejects_final_file_mismatch",
      "lines": [
        193,
        229
      ],
      "summary_l0": "Pytest case test_patch_rejects_final_file_mismatch validating expected behaviour.",
      "contract_l1": "def test_patch_rejects_final_file_mismatch(tmp_path, monkeypatch)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_ingest_and_focus.py"
    },
    {
      "name": "test_ingest_records_edges",
      "kind": "function",
      "qualified_name": "tests.test_ingest_and_focus.test_ingest_records_edges",
      "lines": [
        232,
        252
      ],
      "summary_l0": "Pytest case test_ingest_records_edges validating expected behaviour.",
      "contract_l1": "def test_ingest_records_edges(tmp_path, monkeypatch)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_ingest_and_focus.py"
    },
    {
      "name": "test_focus_cli_traversal",
      "kind": "function",
      "qualified_name": "tests.test_ingest_and_focus.test_focus_cli_traversal",
      "lines": [
        255,
        281
      ],
      "summary_l0": "Pytest case test_focus_cli_traversal validating expected behaviour.",
      "contract_l1": "def test_focus_cli_traversal(tmp_path, monkeypatch)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_ingest_and_focus.py"
    },
    {
      "name": "test_focus_cli_hash_conflict",
      "kind": "function",
      "qualified_name": "tests.test_ingest_and_focus.test_focus_cli_hash_conflict",
      "lines": [
        284,
        291
      ],
      "summary_l0": "Pytest case test_focus_cli_hash_conflict validating expected behaviour.",
      "contract_l1": "def test_focus_cli_hash_conflict(tmp_path, monkeypatch)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_ingest_and_focus.py"
    },
    {
      "name": "test_focus_cli_invalid_handle",
      "kind": "function",
      "qualified_name": "tests.test_ingest_and_focus.test_focus_cli_invalid_handle",
      "lines": [
        294,
        299
      ],
      "summary_l0": "Pytest case test_focus_cli_invalid_handle validating expected behaviour.",
      "contract_l1": "def test_focus_cli_invalid_handle(tmp_path, monkeypatch)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_ingest_and_focus.py"
    },
    {
      "name": "test_inventory_summary",
      "kind": "function",
      "qualified_name": "tests.test_ingest_and_focus.test_inventory_summary",
      "lines": [
        302,
        314
      ],
      "summary_l0": "Pytest case test_inventory_summary validating expected behaviour.",
      "contract_l1": "def test_inventory_summary(tmp_path, monkeypatch)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_ingest_and_focus.py"
    }
  ],
  "tests": [
    {
      "path": "tests/test_ingest_and_focus.py",
      "name": "tests.test_ingest_and_focus.test_ingest_and_focus",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_ingest_and_focus.py",
      "name": "tests.test_ingest_and_focus.test_patch_replaces_symbols",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_ingest_and_focus.py",
      "name": "tests.test_ingest_and_focus.test_ingest_rejects_invalid_agtag",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_ingest_and_focus.py",
      "name": "tests.test_ingest_and_focus.test_ingest_rejects_unsafe_path",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_ingest_and_focus.py",
      "name": "tests.test_ingest_and_focus.test_patch_without_final_payload",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_ingest_and_focus.py",
      "name": "tests.test_ingest_and_focus.test_patch_rejects_final_file_mismatch",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_ingest_and_focus.py",
      "name": "tests.test_ingest_and_focus.test_ingest_records_edges",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_ingest_and_focus.py",
      "name": "tests.test_ingest_and_focus.test_focus_cli_traversal",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_ingest_and_focus.py",
      "name": "tests.test_ingest_and_focus.test_focus_cli_hash_conflict",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_ingest_and_focus.py",
      "name": "tests.test_ingest_and_focus.test_focus_cli_invalid_handle",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_ingest_and_focus.py",
      "name": "tests.test_ingest_and_focus.test_inventory_summary",
      "covers": [],
      "status": "new"
    }
  ]
}
<!--AGTAG v1 END-->
"""
