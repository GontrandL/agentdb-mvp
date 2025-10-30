import ast
import os, sys, sqlite3, hashlib, json, io, re, textwrap, subprocess, time, shutil, fnmatch
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Set
from jsonschema import validate as jsonschema_validate, ValidationError
import click
from agentdb.focus import FocusGraph
from agentdb.migrations import MigrationRunner

DB_DIR = ".agentdb"
DB_FILE = os.path.join(DB_DIR, "agent.sqlite")
# Schema is at project root: from src/agentdb/core.py go up 2 levels
# Schema file retained for legacy tooling (migrations reference it directly).
SCHEMA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "schema.sql")

# Security Fix V-3: AGTAG DoS Protection (2025-10-29)
# Prevent oversized or deeply nested JSON from causing DoS
MAX_AGTAG_SIZE = 100_000  # 100KB max (6.6x safety margin over current max ~15KB)
MAX_JSON_DEPTH = 10       # Maximum nesting depth for JSON objects/arrays

AGTAG_START = "\n\n<!--AGTAG v1 START-->"  # HTML comment to avoid breaking code in many langs
AGTAG_END   = "<!--AGTAG v1 END-->"

AGTAG_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["version", "symbols"],
    "properties": {
        "version": {"type": "string", "enum": ["v1"]},
        "symbols": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "kind"],
                "properties": {
                    "path": {"type": "string"},
                    "name": {"type": "string"},
                    "kind": {"type": "string"},
                    "qualified_name": {"type": "string"},
                    "signature": {"type": "string"},
                    "summary_l0": {"type": "string"},
                    "contract_l1": {"type": "string"},
                    "pseudocode_l2": {"type": ["string", "null"]},
                    "ast_excerpt_l3": {"type": "object"},
                    "ast_l3": {"type": "object"},
                    "lines": {
                        "type": "array",
                        "items": {"type": ["integer", "null"]},
                        "minItems": 2,
                        "maxItems": 2
                    }
                },
                "additionalProperties": True
            }
        },
        "docs": {"type": "array"},
        "tests": {"type": "array"}
    },
    "additionalProperties": True
}


class IngestError(Exception):
    """Exception raised when ingest validation fails."""

    def __init__(self, payload: Dict[str, Any]):
        super().__init__(payload.get("hint") or payload.get("error"))
        self.payload = payload

def sha256_bytes(b: bytes) -> str:
    """Return a SHA-256 content hash string for the given bytes."""
    return "sha256:" + hashlib.sha256(b).hexdigest()


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return bool(row)



def ensure_db() -> sqlite3.Connection:
    """Create (if needed) and return a connection to the AgentDB database."""
    os.makedirs(DB_DIR, exist_ok=True)
    first = not os.path.exists(DB_FILE)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    runner = MigrationRunner(conn)
    if first:
        runner.apply()
    pending = runner.get_pending_migrations()
    if pending:
        versions = [meta.version for meta in pending]
        conn.close()
        raise RuntimeError(
            "Database schema is outdated. Pending migrations: "
            f"{versions}. Run 'agentdb migrate' to upgrade."
        )
    return conn



def get_file_hash(path: str) -> Optional[str]:
    """Compute a SHA-256 hash for a file path, returning None if the file is missing."""
    try:
        with open(path, "rb") as f:
            return sha256_bytes(f.read())
    except FileNotFoundError:
        return None


def split_agtag(content: str) -> tuple[str, Optional[str]]:
    """Separate file content from a trailing AGTAG block, returning (content, agtag_block)."""
    idx = content.rfind(AGTAG_START)
    if idx == -1:
        return content, None
    tail = content[idx:]
    if AGTAG_END not in tail:
        return content, None
    return content[:idx], tail

def ensure_repo_relative_path(path: str) -> str:
    """Normalize and validate that a repo-relative path stays inside the working tree.

    Args:
        path: Candidate path provided by the agent.

    Returns:
        Normalized path string safe to use on disk.

    Raises:
        ValueError: If the path is absolute or escapes the repository root.
    """
    norm = os.path.normpath(path)
    if os.path.isabs(norm):
        raise ValueError("Absolute paths are not allowed")
    if norm.startswith(".."):
        raise ValueError("Path must stay within repository")
    base = os.path.abspath(".")
    abs_path = os.path.abspath(norm)
    if not abs_path.startswith(base + os.sep) and abs_path != base:
        raise ValueError("Path escapes repository root")
    return norm

def validate_agtag_data(agtag: Dict[str, Any], repo_path: str) -> None:
    """Validate the parsed AGTAG payload against the JSON schema and invariants.

    Args:
        agtag: Parsed JSON dictionary extracted from the AGTAG block.
        repo_path: File path used only for error context.

    Raises:
        ValueError: If the AGTAG version or symbol metadata is invalid.
        ValidationError: When JSON schema validation fails.
    """
    jsonschema_validate(instance=agtag, schema=AGTAG_SCHEMA)
    if agtag.get("version") != "v1":
        raise ValueError("Unsupported AGTAG version (expected v1)")
    # Optional: ensure each symbol names lines correctly shaped
    for symbol in agtag.get("symbols", []):
        lines = symbol.get("lines") or []
        if lines and len(lines) != 2:
            raise ValueError(f"Symbol {symbol.get('name')} has invalid lines array")

def extract_final_file_payload(diff_text: str) -> Tuple[Optional[str], Optional[Tuple[int, int]]]:
    """Parse an optional AGTAG final file payload from a diff.

    Args:
        diff_text: Unified diff text possibly containing an AGTAG final file block.

    Returns:
        Tuple of (final_file_content or None, span indices or None).

    Raises:
        ValueError: If the payload block is malformed.
    """
    match = re.search(r"AGTAG_PATCH_FINAL_FILE\s*\{.*?\}\s*END", diff_text, re.S)
    if not match:
        return None, None
    final_block = match.group(0)
    jstart = final_block.find("{")
    jend = final_block.rfind("}")
    payload = json.loads(final_block[jstart:jend+1])
    final_file = payload.get("final_file")
    if final_file is None:
        raise ValueError("AGTAG_PATCH_FINAL_FILE missing final_file field")
    return final_file, (match.start(), match.end())

def apply_unified_diff_to_text(original: str, diff_text: str, repo_path: str) -> str:
    """Apply a unified diff string to the original file contents.

    Args:
        original: Original file text to patch.
        diff_text: Unified diff payload.
        repo_path: Path of the file being patched (used for verification).

    Returns:
        The patched file contents.

    Raises:
        ValueError: If headers, hunks, or context lines are inconsistent.
    """
    diff_lines = diff_text.splitlines()
    original_lines = original.splitlines()
    # Track trailing newline
    original_has_trailing_newline = original.endswith("\n")
    patched_lines: List[str] = []
    idx = 0
    i = 0
    current_file = None
    applied_hunk = False

    while i < len(diff_lines):
        line = diff_lines[i]
        if line.startswith("--- "):
            current_file = line[4:].strip().split("\t")[0]
            i += 1
            continue
        if line.startswith("+++ "):
            new_file = line[4:].strip().split("\t")[0]
            if current_file is None:
                raise ValueError("Diff is missing original file header")
            # Verify target path
            def normalize_header(header: str) -> str:
                if header.startswith("a/") or header.startswith("b/"):
                    header = header[2:]
                return os.path.normpath(header)
            expected = normalize_header(new_file)
            # Some diffs use /dev/null etc. We only accept same path
            header_path = expected
            if header_path != os.path.normpath(repo_path):
                raise ValueError(f"Diff targets '{header_path}' but patch path is '{repo_path}'")
            i += 1
            continue
        if line.startswith("@@ "):
            hunk_header = line
            m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", hunk_header)
            if not m:
                raise ValueError(f"Malformed hunk header: {hunk_header}")
            a_start = int(m.group(1))
            applied_hunk = True
            # Copy untouched lines before this hunk
            desired_idx = a_start - 1
            if desired_idx < idx:
                raise ValueError("Overlapping hunks or repeated context in diff")
            patched_lines.extend(original_lines[idx:desired_idx])
            idx = desired_idx
            i += 1
            # Process hunk body
            while i < len(diff_lines):
                hunk_line = diff_lines[i]
                if hunk_line.startswith("@@ "):
                    break
                if hunk_line.startswith("--- ") or hunk_line.startswith("+++ "):
                    break
                if hunk_line.startswith("\\ No newline at end of file"):
                    i += 1
                    continue
                if hunk_line.startswith(" "):
                    expected = hunk_line[1:]
                    if idx >= len(original_lines) or original_lines[idx] != expected:
                        raise ValueError("Context line mismatch while applying diff")
                    patched_lines.append(expected)
                    idx += 1
                elif hunk_line.startswith("-"):
                    expected = hunk_line[1:]
                    if idx >= len(original_lines) or original_lines[idx] != expected:
                        raise ValueError("Deletion line mismatch while applying diff")
                    idx += 1
                elif hunk_line.startswith("+"):
                    patched_lines.append(hunk_line[1:])
                else:
                    raise ValueError(f"Unsupported diff line: {hunk_line}")
                i += 1
            continue
        i += 1

    patched_lines.extend(original_lines[idx:])
    if not applied_hunk:
        raise ValueError("Diff contained no hunks to apply")
    result = "\n".join(patched_lines)
    if original_has_trailing_newline and not result.endswith("\n"):
        result += "\n"
    return result

def check_json_depth(obj: Any, max_depth: int = MAX_JSON_DEPTH, current_depth: int = 0) -> None:
    """Ensure a JSON payload does not exceed the maximum nesting depth.

    Args:
        obj: JSON object to check (dict, list, or primitive).
        max_depth: Maximum depth permitted.
        current_depth: Current recursion depth (internal use).

    Raises:
        ValueError: If the payload exceeds the allowed depth.
    """
    if current_depth > max_depth:
        raise ValueError(
            f"JSON nesting too deep: exceeds {max_depth} levels "
            f"(current depth: {current_depth}). "
            f"This may indicate a malicious or malformed AGTAG block."
        )

    if isinstance(obj, dict):
        for key, value in obj.items():
            check_json_depth(value, max_depth, current_depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            check_json_depth(item, max_depth, current_depth + 1)
    # Primitives (str, int, bool, None) don't increase depth


def parse_agtag_block(block: str, repo_path: str) -> Dict[str, Any]:
    """Parse and validate an AGTAG block with size and depth defenses.

    Args:
        block: Raw string including AGTAG start/end markers.
        repo_path: Path used for contextual error reporting.

    Returns:
        Parsed JSON dictionary representing the AGTAG payload.

    Raises:
        ValueError: If the block is missing JSON, exceeds size/depth limits, or fails validation.
    """
    # Extract JSON inside AGTAG markers
    jstart = block.find("{")
    jend = block.rfind("}")
    if jstart == -1 or jend == -1:
        raise ValueError("AGTAG block missing JSON")

    jtxt = block[jstart:jend+1]

    # Protection 1: Size limit (prevent memory exhaustion)
    if len(jtxt) > MAX_AGTAG_SIZE:
        raise ValueError(
            f"AGTAG JSON too large: {len(jtxt):,} bytes "
            f"(max {MAX_AGTAG_SIZE:,} bytes). "
            f"Consider splitting into multiple symbols or reducing metadata."
        )

    # Protection 2: Parse JSON
    try:
        data = json.loads(jtxt)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in AGTAG block: {e}")

    # Protection 3: Depth limit (prevent recursion DoS)
    check_json_depth(data, max_depth=MAX_JSON_DEPTH)

    # Protection 4: Schema validation (existing)
    validate_agtag_data(data, repo_path)

    return data


def _ingest_file_content(
    conn: sqlite3.Connection,
    safe_path: str,
    content: str,
    *,
    write_to_disk: bool = True,
) -> Dict[str, Any]:
    file_hash = sha256_bytes(content.encode("utf-8"))
    row = conn.execute("SELECT db_state FROM files WHERE repo_path=?", (safe_path,)).fetchone()
    state = row[0] if row else "missing"
    if state != "missing":
        raise IngestError({
            "error": "indexed_file_rejects_full_content",
            "path": safe_path,
            "hint": "Use agentdb patch instead",
        })

    code, agtag_block = split_agtag(content)
    if not agtag_block:
        raise IngestError({
            "error": "agtag_missing",
            "hint": "Append an AGTAG block at EOF",
        })

    try:
        agtag = parse_agtag_block(agtag_block, safe_path)
    except (ValidationError, ValueError) as exc:
        raise IngestError({
            "error": "agtag_invalid",
            "hint": str(exc),
            "path": safe_path,
        }) from exc

    if write_to_disk:
        os.makedirs(os.path.dirname(safe_path) or ".", exist_ok=True)
        normalized_content = content.rstrip("\n") + "\n"
        with open(safe_path, "w", encoding="utf-8") as f_handle:
            f_handle.write(normalized_content)

    try:
        upsert_symbols(conn, safe_path, agtag, code)
    except ValueError as exc:
        raise IngestError({
            "error": "agtag_symbol_invalid",
            "hint": str(exc),
            "path": safe_path,
        }) from exc

    upsert_file(conn, safe_path, file_hash, "indexed")
    conn.execute(
        "INSERT INTO ops_log(op, details) VALUES(?,?)",
        ("ingest_file", json.dumps({"path": safe_path})),
    )
    conn.commit()
    return {"ok": True, "path": safe_path, "file_hash": file_hash}


def _collect_directory_files(directory: Path, patterns: List[str], excludes: List[str]) -> List[Path]:
    candidates = set()
    include_patterns = patterns or ["*"]
    exclude_patterns = excludes or []
    for pattern in include_patterns:
        for candidate in directory.rglob(pattern):
            if not candidate.is_file():
                continue
            rel = candidate.relative_to(directory).as_posix()
            if any(fnmatch.fnmatch(rel, ex) for ex in exclude_patterns):
                continue
            candidates.add(candidate)
    return sorted(candidates)


def _maybe_auto_tag(content: str, safe_path: str, auto_tag: bool) -> str:
    if not auto_tag:
        return content
    if safe_path.lower().endswith((".md", ".markdown")) and AGTAG_START not in content:
        from agentdb.auto_tagger import generate_agtag  # Lazy import to avoid cost when unused
        return generate_agtag(content, safe_path)
    return content
def upsert_file(conn: sqlite3.Connection, repo_path: str, file_hash: str, state: str):
    """Insert or update file metadata for the given repository path."""
    conn.execute(
        "INSERT INTO files(repo_path, file_hash, db_state) VALUES(?,?,?) "
        "ON CONFLICT(repo_path) DO UPDATE SET file_hash=excluded.file_hash, db_state=excluded.db_state, last_seen=CURRENT_TIMESTAMP",
        (repo_path, file_hash, state)
    )


def _delete_edges_for_symbol_ids(cur: sqlite3.Cursor, symbol_ids: List[int]) -> None:
    """Remove edge rows referencing any of the provided symbol IDs."""
    if not symbol_ids:
        return
    placeholders = ",".join("?" * len(symbol_ids))
    cur.execute(f"DELETE FROM edges WHERE src_id IN ({placeholders})", symbol_ids)
    cur.execute(f"DELETE FROM edges WHERE dst_id IN ({placeholders})", symbol_ids)


def clear_symbols(conn: sqlite3.Connection, repo_path: str) -> None:
    """Delete symbols, FTS rows, and edges for a given repo path."""
    cur = conn.cursor()
    symbol_rows = cur.execute("SELECT id FROM symbols WHERE repo_path=?", (repo_path,)).fetchall()
    symbol_ids = [row[0] for row in symbol_rows]
    _delete_edges_for_symbol_ids(cur, symbol_ids)
    cur.execute("DELETE FROM symbols WHERE repo_path=?", (repo_path,))
    cur.execute("DELETE FROM symbols_fts WHERE repo_path=?", (repo_path,))


def _find_symbol_node(module_ast: Optional[ast.AST], symbol: Dict[str, Any]) -> Optional[ast.AST]:
    """Locate the AST node corresponding to a symbol definition."""
    if module_ast is None:
        return None
    target_name = symbol.get("name")
    target_line = symbol.get("start_line")
    if not target_name or target_line is None:
        return None
    for node in ast.walk(module_ast):
        if isinstance(node, ast.ClassDef):
            if symbol.get("kind", "").lower() == "class" and node.name == target_name and getattr(node, "lineno", None) == target_line:
                return node
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == target_name and getattr(node, "lineno", None) == target_line:
                return node
    return None


def _collect_call_targets(func_node: ast.AST) -> Set[str]:
    """Collect function names invoked inside a function or method definition."""
    targets: Set[str] = set()
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            callee = node.func
            if isinstance(callee, ast.Name):
                targets.add(callee.id)
            elif isinstance(callee, ast.Attribute):
                # For attribute calls (obj.method()), use the attribute name as best-effort match.
                targets.add(callee.attr)
    return targets


def _collect_inheritance_targets(class_node: ast.ClassDef) -> Set[str]:
    """Collect class names referenced as bases for inheritance."""
    targets: Set[str] = set()
    for base in class_node.bases:
        if isinstance(base, ast.Name):
            targets.add(base.id)
        elif isinstance(base, ast.Attribute):
            targets.add(base.attr)
    return targets


def _build_symbol_edges(module_ast: Optional[ast.AST], symbols: List[Dict[str, Any]]) -> List[Tuple[int, int, str]]:
    """Produce edge tuples for intra-file relationships between symbols."""
    if module_ast is None or not symbols:
        return []
    name_to_id = {s["name"]: s["id"] for s in symbols if s.get("name")}
    edges: Set[Tuple[int, int, str]] = set()
    for symbol in symbols:
        node = _find_symbol_node(module_ast, symbol)
        if node is None:
            continue
        symbol_id = symbol["id"]
        kind = (symbol.get("kind") or "").lower()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            call_targets = _collect_call_targets(node)
            for target in call_targets:
                dst_id = name_to_id.get(target)
                if dst_id and dst_id != symbol_id:
                    edges.add((symbol_id, dst_id, "calls"))
        elif isinstance(node, ast.ClassDef) or kind == "class":
            inherits = _collect_inheritance_targets(node) if isinstance(node, ast.ClassDef) else set()
            for target in inherits:
                dst_id = name_to_id.get(target)
                if dst_id and dst_id != symbol_id:
                    edges.add((symbol_id, dst_id, "inherits"))
    return list(edges)


def upsert_symbols(conn: sqlite3.Connection, repo_path: str, agtag: Dict[str, Any], full_content: str):
    """Rebuild symbol, FTS, and edge metadata for a file based on its AGTAG payload."""
    clear_symbols(conn, repo_path)
    lines_cache = full_content.splitlines()
    total_lines = len(lines_cache)
    parsed_ast: Optional[ast.AST] = None
    if repo_path.endswith(".py"):
        try:
            parsed_ast = ast.parse(full_content)
        except SyntaxError:
            parsed_ast = None
    symbol_rows: List[Tuple[Any, ...]] = []
    for s in agtag.get("symbols", []):
        name = s.get("name")
        kind = s.get("kind")
        raw_lines = s.get("lines") or [None, None]
        if len(raw_lines) < 2:
            raw_lines = list(raw_lines) + [None] * (2 - len(raw_lines))
        start_line = raw_lines[0]
        end_line = raw_lines[1]
        start_line = int(start_line) if start_line is not None else None
        end_line = int(end_line) if end_line is not None else None
        signature = s.get("signature")
        l0 = s.get("summary_l0")
        l1 = s.get("contract_l1")
        l2 = s.get("pseudocode_l2")
        l3_payload = s.get("ast_excerpt_l3")
        if not l3_payload and s.get("ast_l3"):
            l3_payload = s.get("ast_l3")
        l3 = json.dumps(l3_payload) if l3_payload else None
        # content_hash for slice if lines provided; else whole file
        if start_line is not None and end_line is not None:
            if start_line < 1 or end_line < start_line:
                raise ValueError(f"Invalid line range for symbol '{name}'")
            if end_line > total_lines:
                raise ValueError(f"Symbol '{name}' references lines beyond file length")
            code_slice = "\n".join(lines_cache[start_line-1:end_line])
            chash = sha256_bytes(code_slice.encode("utf-8"))
        else:
            chash = sha256_bytes(full_content.encode("utf-8"))
        symbol_rows.append(
            (repo_path, name, kind, signature, start_line, end_line, chash, l0, l1, l2, l3)
        )

    cur = conn.cursor()
    if symbol_rows:
        cur.executemany(
            "INSERT INTO symbols(repo_path, name, kind, signature, start_line, end_line, content_hash, l0_overview, l1_contract, l2_pseudocode, l3_ast_json) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            symbol_rows
        )
        cur.execute(
            "INSERT INTO symbols_fts(rowid, repo_path, name, l0_overview, l1_contract) "
            "SELECT id, repo_path, name, l0_overview, l1_contract FROM symbols WHERE repo_path=?",
            (repo_path,)
        )
        symbol_rows_db = cur.execute(
            "SELECT id, name, kind, start_line, end_line FROM symbols WHERE repo_path=?",
            (repo_path,)
        ).fetchall()
        inserted_symbols = [dict(row) for row in symbol_rows_db]
        edges = _build_symbol_edges(parsed_ast, inserted_symbols)
        if edges:
            cur.executemany(
                "INSERT OR IGNORE INTO edges(src_id, dst_id, edge_type) VALUES(?,?,?)",
                edges
            )
    conn.commit()

@click.group()
def cli():
    pass

@cli.command()
def init():
    """Bootstrap `.agentdb/agent.sqlite` by creating the schema and applying migrations.

    Emits a JSON message and exits with code 2 on failure.
    """
    try:
        conn = ensure_db()
    except sqlite3.OperationalError as exc:
        click.echo(json.dumps({
            "error": "init_failed",
            "hint": f"Database initialization failed: {exc}. "
                    "Check filesystem permissions and ensure SQLite extensions are available."
        }))
        sys.exit(2)
    except RuntimeError as exc:
        click.echo(json.dumps({
            "error": "db_version_mismatch",
            "hint": str(exc)
        }))
        sys.exit(2)
    except Exception as exc:  # pylint: disable=broad-except
        click.echo(json.dumps({
            "error": "init_failed",
            "hint": f"Unexpected error during init: {exc}"
        }))
        sys.exit(2)
    else:
        conn.close()
        click.echo(f"OK: initialized {DB_FILE}")

@cli.command()
@click.option("--summary", is_flag=True, help="Include aggregate summary in output")
def inventory(summary):
    """List tracked files and optionally emit inventory summary statistics.

    Args:
        summary: When True, append aggregate counts after the per-file rows.
    """
    conn = ensure_db()
    rows = conn.execute("SELECT repo_path, file_hash, db_state, last_seen FROM files ORDER BY repo_path").fetchall()
    state_counts: Dict[str, int] = {}
    status_counts: Dict[str, int] = {}
    for r in rows:
        payload = dict(r)
        repo_path = payload["repo_path"]
        try:
            ensure_repo_relative_path(repo_path)
        except ValueError:
            # Entry predates safety checks; treat as-is
            pass
        exists = os.path.exists(repo_path)
        disk_hash = get_file_hash(repo_path) if exists else None
        hash_matches = bool(payload["file_hash"] and disk_hash and payload["file_hash"] == disk_hash)
        if payload["db_state"] == "missing":
            status = "missing_in_db"
        elif not exists:
            status = "missing_on_disk"
        elif hash_matches:
            status = "in_sync"
        else:
            status = "stale_on_disk"
        payload.update({
            "exists_on_disk": exists,
            "disk_hash": disk_hash,
            "hash_matches": hash_matches,
            "status": status,
        })
        state_counts[payload["db_state"]] = state_counts.get(payload["db_state"], 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1
        click.echo(json.dumps(payload))
    if summary:
        click.echo(json.dumps({
            "summary": {
                "by_state": state_counts,
                "by_status": status_counts,
                "total": len(rows)
            }
        }))

@cli.command()
@click.option("--query", required=True, help="Search query string")
@click.option("--fields", default="l0,l1", help="Comma-separated fields to search (l0,l1,l2,l3,l4)")
@click.option("--limit", default=10, type=int, help="Maximum number of results to return")
@click.option("--kind", help="Filter by symbol kind (function, class, method, etc.)")
def search(query, fields, limit, kind):
    """Search symbols by content using FTS5 full-text search.

    Search across symbol levels (L0-L4) to find symbols matching your query.
    By default searches L0 (overview) and L1 (contract) for fast, relevant results.

    Examples:
        agentdb search --query "token strategy"
        agentdb search --query "migration" --fields "l0,l1,l2" --limit 20
        agentdb search --query "validation" --kind "function"
    """
    conn = ensure_db()

    # Parse search fields
    search_fields = [f.strip() for f in fields.split(',')]
    valid_fields = {'l0', 'l1', 'l2', 'l3', 'l4'}
    invalid = [f for f in search_fields if f not in valid_fields]
    if invalid:
        click.echo(json.dumps({
            "error": "invalid_fields",
            "hint": f"Invalid fields: {invalid}. Valid: {list(valid_fields)}"
        }))
        sys.exit(2)

    # Build FTS5 query - search symbols_fts virtual table
    # FTS5 MATCH syntax for contentless index: "symbols_fts MATCH 'query'"
    # symbols_fts columns: repo_path, name, l0_overview, l1_contract

    # Map level names to FTS5 column names
    fts_columns = {
        'l0': 'l0_overview',
        'l1': 'l1_contract',
    }

    # Only l0 and l1 are indexed in FTS5
    indexed_fields = [f for f in search_fields if f in ['l0', 'l1']]

    if not indexed_fields:
        click.echo(json.dumps({
            "error": "no_indexed_fields",
            "hint": "FTS5 only indexes l0 and l1. Use --fields l0,l1 for fast search."
        }))
        sys.exit(2)

    # Simple MATCH query - searches all indexed columns
    # Note: Column-specific syntax (l0_overview:term) doesn't work reliably,
    # so we use simple query which searches all FTS5 columns
    fts_query = f"""
        SELECT
            s.repo_path,
            s.name,
            s.kind,
            s.start_line,
            s.end_line,
            s.l0_overview,
            s.l1_contract,
            s.content_hash,
            fts.rank
        FROM symbols_fts fts
        JOIN symbols s ON fts.rowid = s.id
        WHERE symbols_fts MATCH ?
    """

    # Add kind filter if specified
    params = [query]  # Simple query string
    if kind:
        fts_query += " AND s.kind = ?"
        params.append(kind)

    fts_query += " ORDER BY fts.rank LIMIT ?"
    params.append(limit)

    try:
        results = conn.execute(fts_query, params).fetchall()
    except sqlite3.OperationalError as exc:
        click.echo(json.dumps({
            "error": "fts_query_failed",
            "hint": f"FTS5 query error: {exc}"
        }))
        sys.exit(2)

    # Format results
    output = {
        "query": query,
        "fields": search_fields,
        "kind_filter": kind,
        "count": len(results),
        "limit": limit,
        "results": []
    }

    for row in results:
        output["results"].append({
            "repo_path": row["repo_path"],
            "name": row["name"],
            "kind": row["kind"],
            "lines": [row["start_line"], row["end_line"]],
            "l0_overview": row["l0_overview"],
            "l1_contract": row["l1_contract"],
            "content_hash": row["content_hash"],
            "rank": row["rank"]
        })

    click.echo(json.dumps(output, indent=2))

@cli.command()
@click.option("--path", help="Path of the file being ingested")
@click.option("--directory", type=click.Path(exists=True, file_okay=False), help="Bulk ingest matching files in directory")
@click.option("--pattern", multiple=True, default=("*.md",), show_default=True, help="Glob patterns to include when using --directory")
@click.option("--exclude", multiple=True, default=("node_modules/*",), show_default=True, help="Glob patterns to exclude when using --directory")
@click.option("--auto-tag", is_flag=True, help="Auto-generate AGTAG for markdown files")
def ingest(path, directory, pattern, exclude, auto_tag):
    """Ingest files into AgentDB (single file or bulk directory mode)."""
    if bool(path) == bool(directory):
        click.echo(json.dumps({
            "error": "invalid_arguments",
            "hint": "Specify exactly one of --path or --directory"
        }))
        sys.exit(2)

    conn = ensure_db()
    try:
        if directory:
            dir_path = Path(directory)
            files = _collect_directory_files(dir_path, list(pattern), list(exclude))
            successes: List[Dict[str, Any]] = []
            failures: List[Dict[str, Any]] = []
            with click.progressbar(files, label="Ingesting files") as bar:
                for file_path in bar:
                    rel = os.path.relpath(file_path, Path.cwd())
                    try:
                        safe_path = ensure_repo_relative_path(rel)
                    except ValueError as exc:
                        failures.append({"path": rel, "error": "unsafe_path", "hint": str(exc)})
                        continue
                    try:
                        content = file_path.read_text(encoding="utf-8")
                    except OSError as exc:
                        failures.append({"path": rel, "error": "read_failed", "hint": str(exc)})
                        continue
                    content = _maybe_auto_tag(content, safe_path, auto_tag)
                    try:
                        result = _ingest_file_content(
                            conn,
                            safe_path,
                            content,
                            write_to_disk=auto_tag,
                        )
                        successes.append(result)
                    except IngestError as exc:
                        payload = dict(exc.payload)
                        payload.setdefault("path", safe_path)
                        failures.append(payload)
            payload: Dict[str, Any] = {
                "ok": not failures,
                "files_ingested": len(successes),
                "results": successes,
            }
            if failures:
                payload["errors"] = failures
            click.echo(json.dumps(payload))
            if failures:
                sys.exit(2)
            return

        try:
            safe_path = ensure_repo_relative_path(path)
        except ValueError as exc:
            click.echo(json.dumps({"error": "unsafe_path", "hint": str(exc)}))
            sys.exit(2)
        content = sys.stdin.read()
        content = _maybe_auto_tag(content, safe_path, auto_tag)
        try:
            result = _ingest_file_content(conn, safe_path, content)
        except IngestError as exc:
            click.echo(json.dumps(exc.payload))
            sys.exit(2)
        else:
            click.echo(json.dumps(result))
    finally:
        conn.close()


def parse_handle(handle: str) -> Dict[str, Any]:
    """Parse a ctx:// handle into its components.

    Args:
        handle: Handle string such as ``ctx://path::symbol@sha256:HASH``.

    Returns:
        Dictionary containing repo_path, symbol, hash, and optional level.

    Raises:
        ValueError: If the handle format is invalid.
    """
    # ctx://{repo_path}::[{symbol}]@{hash}[#l{level}]
    # Level suffix is optional (used by zoom, not by focus)
    m = re.match(r"ctx://(.+?)::(.+?)@([^#]+)(?:#l(\d+))?", handle)
    if not m:
        raise ValueError("Invalid handle")
    level = int(m.group(4)) if m.group(4) else None
    return {"repo_path": m.group(1), "symbol": m.group(2), "hash": m.group(3), "level": level}

@cli.command()
@click.option("--handle", required=True)
@click.option("--depth", required=False, default=1, type=int)
@click.option(
    "--types",
    "types_filter",
    default="",
    help="Comma-separated relationship types to include (e.g., calls,inherits)",
)
def focus(handle, depth, types_filter):
    """Return symbol context plus neighbors up to the requested depth.

    Args:
        handle: ctx:// handle describing the target symbol.
        depth: Number of hops to traverse for neighbors.
        types_filter: Optional comma separated list of edge types to include.
    """
    if depth < 0:
        click.echo(json.dumps({"error": "bad_depth", "hint": "Depth must be >= 0"}))
        sys.exit(2)
    include_types = [t.strip() for t in types_filter.split(",") if t.strip()]
    try:
        h = parse_handle(handle)
    except ValueError:
        click.echo(json.dumps({
            "error": "handle_invalid",
            "hint": "Expected format ctx://path::symbol@sha256:HASH"
        }))
        sys.exit(2)
    try:
        conn = ensure_db()
    except RuntimeError as exc:
        click.echo(json.dumps({
            "error": "db_version_mismatch",
            "hint": str(exc)
        }))
        sys.exit(2)
    except Exception as exc:  # pylint: disable=broad-except
        click.echo(json.dumps({
            "error": "db_unavailable",
            "hint": f"Unable to open AgentDB database: {exc}"
        }))
        sys.exit(2)
    if h["symbol"] == "ANY":
        click.echo(json.dumps({
            "error": "symbol_required",
            "hint": "Provide a concrete symbol in the handle (no ANY wildcard)."
        }))
        sys.exit(2)
    file_row = conn.execute(
        "SELECT file_hash, db_state FROM files WHERE repo_path=?",
        (h["repo_path"],)
    ).fetchone()
    if not file_row or file_row["db_state"] != "indexed":
        click.echo(json.dumps({
            "error": "not_indexed",
            "hint": "Ingest the file before requesting focus context."
        }))
        sys.exit(2)
    handle_hash = h["hash"]
    if handle_hash and handle_hash.lower() != "sha256:any":
        expected_hash = file_row["file_hash"]
        if expected_hash != handle_hash:
            click.echo(json.dumps({
                "error": "hash_conflict",
                "expected": expected_hash,
                "handle_hash": handle_hash
            }))
            sys.exit(2)
    graph = FocusGraph(conn)
    context = graph.get_context(
        h["repo_path"],
        h["symbol"],
        depth,
        include_types or None
    )
    if "error" in context:
        click.echo(json.dumps(context))
        conn.close()
        sys.exit(2)
    result: Dict[str, Any] = {
        "handle": handle,
        "depth": depth,
        "filters": include_types,
    }
    result.update(context)
    conn.close()
    click.echo(json.dumps(result))


@cli.command()
@click.option("--target-version", type=int, help="Migrate to specific version")
@click.option("--dry-run", is_flag=True, help="Show pending migrations without applying")
@click.option("--rollback", type=int, help="Rollback the specified migration version")
def migrate(target_version, dry_run, rollback):
    """Apply, preview, or rollback database schema migrations."""
    if dry_run and rollback is not None:
        click.echo(json.dumps({
            "error": "invalid_options",
            "hint": "--dry-run cannot be combined with --rollback"
        }))
        sys.exit(2)

    db_path = Path(DB_FILE)
    if not db_path.exists():
        click.echo(json.dumps({
            "error": "no_db_found",
            "hint": "No database found. Run 'agentdb init' first."
        }))
        sys.exit(2)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    legacy = _table_exists(conn, "schema_migrations") and not _table_exists(conn, "symbols")
    if legacy and not dry_run and rollback is None:
        conn.executescript(
            "DROP TABLE IF EXISTS schema_migrations; DROP TABLE IF EXISTS db_version;"
        )
        conn.commit()
    runner = MigrationRunner(conn)
    try:
        if rollback is not None:
            try:
                runner.rollback(rollback)
            except Exception as exc:
                click.echo(json.dumps({
                    "error": "rollback_failed",
                    "hint": str(exc)
                }))
                sys.exit(2)
            else:
                click.echo(json.dumps({
                    "ok": True,
                    "rolled_back": rollback,
                    "current_version": runner.get_current_version()
                }))
                return

        pending = runner.get_pending_migrations(target_version)
        if legacy and dry_run and not any(meta.version == 1 for meta in pending):
            base_meta = runner._load_migration_by_version(1)
            if base_meta:
                pending = [base_meta] + pending
        if dry_run:
            payload = {
                "current_version": runner.get_current_version(),
                "target_version": target_version or runner.get_latest_version(),
                "pending_migrations": [
                    {
                        "version": meta.version,
                        "description": meta.description,
                        "checksum": meta.checksum,
                    }
                    for meta in pending
                ],
                "dry_run": True,
                "backup": None,
            }
            click.echo(json.dumps(payload))
            return

        if not pending:
            click.echo(json.dumps({
                "ok": True,
                "message": "Database already up to date",
                "current_version": runner.get_current_version(),
                "migrations_applied": []
            }))
            return

        backup_path = db_path.parent / f"agent.sqlite.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        shutil.copy(db_path, backup_path)
        from_version = runner.get_current_version()
        applied = runner.apply(target_version)
        labels = []
        cursor = from_version
        for version in applied:
            labels.append(f"v{cursor}_to_v{version}")
            cursor = version
        payload = {
            "ok": True,
            "from_version": from_version,
            "to_version": runner.get_current_version(),
            "migrations_applied": labels,
            "backup": str(backup_path)
        }
        click.echo(json.dumps(payload))
    finally:
        conn.close()


@cli.command()
@click.option("--handle", required=True)
@click.option("--level", required=True, type=int)
def zoom(handle, level):
    """Return progressive disclosure slices (L0-L4) for a given handle.

    Args:
        handle: ctx:// handle referencing a symbol.
        level: Target disclosure level (0-4 inclusive).
    """
    if level < 0 or level > 4:
        click.echo(json.dumps({"error": "bad_level"})); sys.exit(2)
    conn = ensure_db()
    h = parse_handle(handle)
    r = conn.execute(
        "SELECT id, repo_path, name, l0_overview, l1_contract, l2_pseudocode, l3_ast_json, start_line, end_line FROM symbols WHERE repo_path=? AND (name=? OR ?='ANY') LIMIT 1",
        (h["repo_path"], h["symbol"], h["symbol"])
    ).fetchone()
    if not r:
        click.echo(json.dumps({"error":"not_found","hint":"ingest or lower your expectations"})); sys.exit(2)
    data = {"l0": r["l0_overview"], "l1": r["l1_contract"]}
    if level >= 2: data["l2"] = r["l2_pseudocode"]
    if level >= 3: data["l3"] = json.loads(r["l3_ast_json"] or "{}")
    if level >= 4:
        # Return file slice
        try:
            with open(h["repo_path"], "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
            s, e = (r["start_line"] or 1), (r["end_line"] or len(lines))
            data["l4"] = "\n".join(lines[s-1:e])
        except Exception as ex:
            data["l4_error"] = str(ex)
    click.echo(json.dumps({"handle": handle, "level": level, "data": data}))

@cli.command()
@click.option("--path", required=True)
@click.option("--hash-before", "hash_before", required=True)
def patch(path, hash_before):
    """Apply a unified diff to an indexed file and refresh metadata if hashes match.

    Args:
        path: Repository-relative file path to patch.
        hash_before: Expected pre-image hash to protect against stale edits.
    """
    conn = ensure_db()
    try:
        safe_path = ensure_repo_relative_path(path)
    except ValueError as exc:
        click.echo(json.dumps({"error":"unsafe_path","hint":str(exc)}))
        sys.exit(2)
    row = conn.execute("SELECT file_hash, db_state FROM files WHERE repo_path=?", (safe_path,)).fetchone()
    if not row or row["db_state"] != "indexed":
        click.echo(json.dumps({"error":"not_indexed","hint":"ingest first"})); sys.exit(2)
    if row["file_hash"] != hash_before:
        click.echo(json.dumps({"error":"hash_conflict","current":row['file_hash']})); sys.exit(2)
    diff = sys.stdin.read()
    try:
        final_payload, span = extract_final_file_payload(diff)
    except ValueError as exc:
        click.echo(json.dumps({"error":"final_file_invalid","hint":str(exc)}))
        sys.exit(2)
    diff_to_apply = diff
    if span:
        diff_to_apply = diff[:span[0]]
    with open(safe_path, "r", encoding="utf-8") as f:
        original = f.read()
    try:
        patched_content = apply_unified_diff_to_text(original, diff_to_apply, safe_path)
    except ValueError as exc:
        click.echo(json.dumps({"error":"patch_failed","hint":str(exc)}))
        sys.exit(2)
    if final_payload is not None:
        if patched_content.rstrip("\n") != final_payload.rstrip("\n"):
            click.echo(json.dumps({"error":"final_file_mismatch","hint":"AGTAG_PATCH_FINAL_FILE does not match applied diff"}))
            sys.exit(2)
        final_content = final_payload
    else:
        final_content = patched_content
    final_content = final_content.rstrip("\n") + "\n"
    with open(safe_path, "w", encoding="utf-8") as f:
        f.write(final_content)
    new_hash = sha256_bytes(final_content.encode("utf-8"))
    # Re-ingest symbols from new content
    code, agtag_block = split_agtag(final_content)
    if agtag_block:
        try:
            agtag = parse_agtag_block(agtag_block, safe_path)
            upsert_symbols(conn, safe_path, agtag, code)
        except (ValidationError, ValueError) as exc:
            click.echo(json.dumps({"error":"agtag_invalid","hint":str(exc)}))
            sys.exit(2)
    else:
        clear_symbols(conn, safe_path)
    # Update file hash
    upsert_file(conn, safe_path, new_hash, "indexed")
    conn.execute("INSERT INTO ops_log(op, details) VALUES(?,?)", ("patch", json.dumps({"path":safe_path})))
    conn.commit()
    click.echo(json.dumps({"ok":True,"path":safe_path,"file_hash":new_hash}))


# ============================================================================
# CLI Commands for Extended Schema Manager Classes
# ============================================================================

@cli.group()
def agent():
    """Manage agents (register, list, update status)."""
    pass


@agent.command("register")
@click.option("--agent-id", required=True, help="Unique agent identifier")
@click.option("--role", required=True, help="Agent role (e.g., 'developer', 'reviewer')")
@click.option("--capabilities", required=True, help="Comma-separated list of capabilities")
@click.option("--status", default="active", help="Initial status (active, idle, busy, offline)")
@click.option("--mission", help="Current mission description")
def agent_register(agent_id, role, capabilities, status, mission):
    """Register a new agent or update existing agent."""
    from agentdb.agent_manager import AgentManager

    conn = ensure_db()
    mgr = AgentManager(conn)

    caps_list = [c.strip() for c in capabilities.split(",")]
    agent_data = mgr.register_agent(
        agent_id=agent_id,
        role=role,
        capabilities=caps_list,
        status=status,
        current_mission=mission
    )

    conn.close()
    click.echo(json.dumps({"ok": True, "agent": agent_data}))


@agent.command("list")
@click.option("--role", help="Filter by role")
@click.option("--status", help="Filter by status")
def agent_list(role, status):
    """List all registered agents."""
    from agentdb.agent_manager import AgentManager

    conn = ensure_db()
    mgr = AgentManager(conn)

    agents = mgr.list_agents(role=role, status=status)

    conn.close()
    click.echo(json.dumps({"ok": True, "agents": agents, "count": len(agents)}))


@agent.command("context")
@click.option("--agent-id", required=True, help="Agent identifier")
@click.option("--level", default="L1", help="Context level (L0, L1, L2)")
def agent_context(agent_id, level):
    """Get agent context for prompt assembly."""
    from agentdb.agent_manager import AgentManager

    conn = ensure_db()
    mgr = AgentManager(conn)

    context = mgr.get_agent_context(agent_id, level=level)

    conn.close()
    click.echo(json.dumps({"ok": True, "context": context}))


@agent.command("update-status")
@click.option("--agent-id", required=True, help="Agent identifier")
@click.option("--status", required=True, help="New status")
@click.option("--mission", help="Update current mission")
def agent_update_status(agent_id, status, mission):
    """Update agent status and optionally mission."""
    from agentdb.agent_manager import AgentManager

    conn = ensure_db()
    mgr = AgentManager(conn)

    agent_data = mgr.update_agent_status(agent_id, status, mission)

    conn.close()
    click.echo(json.dumps({"ok": True, "agent": agent_data}))


@cli.group()
def env():
    """Manage environment state (set, get, list variables)."""
    pass


@env.command("set")
@click.option("--key", required=True, help="Environment variable key")
@click.option("--value", required=True, help="Environment variable value")
@click.option("--category", default="general", help="Category (system, project, runtime, dependencies, config)")
@click.option("--description", help="Variable description")
def env_set(key, value, category, description):
    """Set or update an environment variable."""
    from agentdb.environment_tracker import EnvironmentTracker

    conn = ensure_db()
    tracker = EnvironmentTracker(conn)

    var_data = tracker.set(key, value, category=category, description=description)

    conn.close()
    click.echo(json.dumps({"ok": True, "variable": var_data}))


@env.command("get")
@click.option("--key", required=True, help="Environment variable key")
def env_get(key):
    """Get a specific environment variable."""
    from agentdb.environment_tracker import EnvironmentTracker

    conn = ensure_db()
    tracker = EnvironmentTracker(conn)

    var_data = tracker.get(key)

    conn.close()
    if var_data:
        click.echo(json.dumps({"ok": True, "variable": var_data}))
    else:
        click.echo(json.dumps({"ok": False, "error": "not_found"}))
        sys.exit(1)


@env.command("list")
@click.option("--category", help="Filter by category")
def env_list(category):
    """List all environment variables."""
    from agentdb.environment_tracker import EnvironmentTracker

    conn = ensure_db()
    tracker = EnvironmentTracker(conn)

    variables = tracker.get_all(category=category)

    conn.close()
    click.echo(json.dumps({"ok": True, "variables": variables, "count": len(variables)}))


@env.command("context")
@click.option("--level", default="L1", help="Context level (L0, L1, L2)")
def env_context(level):
    """Get project environment context for prompt assembly."""
    from agentdb.environment_tracker import EnvironmentTracker

    conn = ensure_db()
    tracker = EnvironmentTracker(conn)

    context = tracker.get_project_context(level=level)

    conn.close()
    click.echo(json.dumps({"ok": True, "context": context}))


@cli.group()
def tool():
    """Manage tool registry (register, list, record usage)."""
    pass


@tool.command("register")
@click.option("--name", required=True, help="Tool name")
@click.option("--type", "tool_type", required=True, help="Tool type (testing, linting, build, etc.)")
@click.option("--description", help="Tool description")
def tool_register(name, tool_type, description):
    """Register a new tool."""
    from agentdb.tool_registry import ToolRegistry

    conn = ensure_db()
    registry = ToolRegistry(conn)

    tool_data = registry.register_tool(name, tool_type, description=description)

    conn.close()
    click.echo(json.dumps({"ok": True, "tool": tool_data}))


@tool.command("list")
@click.option("--type", "tool_type", help="Filter by tool type")
def tool_list(tool_type):
    """List all registered tools."""
    from agentdb.tool_registry import ToolRegistry

    conn = ensure_db()
    registry = ToolRegistry(conn)

    tools = registry.list_tools(tool_type=tool_type)

    conn.close()
    click.echo(json.dumps({"ok": True, "tools": tools, "count": len(tools)}))


@tool.command("record-usage")
@click.option("--name", required=True, help="Tool name")
@click.option("--symbol-id", type=int, help="Symbol ID (if usage was on specific symbol)")
def tool_record_usage(name, symbol_id):
    """Record tool usage."""
    from agentdb.tool_registry import ToolRegistry

    conn = ensure_db()
    registry = ToolRegistry(conn)

    registry.record_usage(name, symbol_id=symbol_id)

    conn.close()
    click.echo(json.dumps({"ok": True, "tool": name}))


@cli.group()
def spec():
    """Manage specifications (create, list, show traceability)."""
    pass


@spec.command("create")
@click.option("--spec-id", required=True, help="Specification ID (e.g., SPEC-001)")
@click.option("--title", required=True, help="Specification title")
@click.option("--description", help="Detailed description")
@click.option("--type", "spec_type", default="feature", help="Type (feature, bug_fix, refactor, enhancement)")
@click.option("--requirements", help="Comma-separated list of requirements")
@click.option("--created-by", default="unknown", help="Agent/user who created this")
def spec_create(spec_id, title, description, spec_type, requirements, created_by):
    """Create a new specification."""
    from agentdb.specification_manager import SpecificationManager

    conn = ensure_db()
    mgr = SpecificationManager(conn)

    reqs_list = None
    if requirements:
        reqs_list = [r.strip() for r in requirements.split(",")]

    spec_data = mgr.create_spec(
        spec_id=spec_id,
        title=title,
        description=description,
        spec_type=spec_type,
        requirements=reqs_list,
        created_by=created_by
    )

    conn.close()
    click.echo(json.dumps({"ok": True, "spec": spec_data}))


@spec.command("list")
@click.option("--status", help="Filter by status")
@click.option("--type", "spec_type", help="Filter by type")
def spec_list(status, spec_type):
    """List all specifications."""
    from agentdb.specification_manager import SpecificationManager

    conn = ensure_db()
    mgr = SpecificationManager(conn)

    specs = mgr.list_specs(status=status, spec_type=spec_type)

    conn.close()
    click.echo(json.dumps({"ok": True, "specs": specs, "count": len(specs)}))


@spec.command("trace")
@click.option("--spec-id", required=True, help="Specification ID")
def spec_trace(spec_id):
    """Get complete traceability matrix for a specification."""
    from agentdb.specification_manager import SpecificationManager

    conn = ensure_db()
    mgr = SpecificationManager(conn)

    trace = mgr.get_traceability(spec_id)

    conn.close()
    click.echo(json.dumps({"ok": True, "traceability": trace}))


@cli.group()
def ticket():
    """Manage tickets/tasks (create, list, update)."""
    pass


@ticket.command("create")
@click.option("--ticket-id", required=True, help="Ticket ID (e.g., TICKET-001)")
@click.option("--title", required=True, help="Ticket title")
@click.option("--description", help="Detailed description")
@click.option("--spec-id", help="Related specification ID")
@click.option("--assigned-to", help="Agent assigned to this ticket")
@click.option("--priority", default="medium", help="Priority (low, medium, high, critical)")
@click.option("--type", "ticket_type", default="task", help="Type (task, bug, feature, test, doc)")
def ticket_create(ticket_id, title, description, spec_id, assigned_to, priority, ticket_type):
    """Create a new ticket."""
    from agentdb.ticket_manager import TicketManager

    conn = ensure_db()
    mgr = TicketManager(conn)

    ticket_data = mgr.create_ticket(
        ticket_id=ticket_id,
        title=title,
        description=description,
        ticket_type=ticket_type,
        spec_id=spec_id,
        assigned_to=assigned_to,
        priority=priority
    )

    conn.close()
    click.echo(json.dumps({"ok": True, "ticket": ticket_data}))


@ticket.command("list")
@click.option("--status", help="Filter by status")
@click.option("--assigned-to", help="Filter by assigned agent")
def ticket_list(status, assigned_to):
    """List all tickets."""
    from agentdb.ticket_manager import TicketManager

    conn = ensure_db()
    mgr = TicketManager(conn)

    tickets = mgr.list_tickets(status=status, assigned_to=assigned_to)

    conn.close()
    click.echo(json.dumps({"ok": True, "tickets": tickets, "count": len(tickets)}))


@ticket.command("from-spec")
@click.option("--spec-id", required=True, help="Specification ID")
@click.option("--assigned-to", required=True, help="Agent to assign tickets to")
@click.option("--auto-estimate", is_flag=True, default=True, help="Auto-estimate hours based on requirement type")
def ticket_from_spec(spec_id, assigned_to, auto_estimate):
    """Auto-create tickets from specification requirements."""
    from agentdb.ticket_manager import TicketManager

    conn = ensure_db()
    mgr = TicketManager(conn)

    tickets = mgr.create_tickets_from_spec(spec_id, assigned_to, auto_estimate=auto_estimate)

    conn.close()
    click.echo(json.dumps({"ok": True, "tickets": tickets, "count": len(tickets)}))


@ticket.command("update-status")
@click.option("--ticket-id", required=True, help="Ticket ID")
@click.option("--status", required=True, help="New status (todo, in_progress, done, blocked, cancelled)")
@click.option("--actual-hours", type=float, help="Actual hours spent (when marking done)")
def ticket_update_status(ticket_id, status, actual_hours):
    """Update ticket status."""
    from agentdb.ticket_manager import TicketManager

    conn = ensure_db()
    mgr = TicketManager(conn)

    ticket_data = mgr.update_ticket_status(ticket_id, status, actual_hours=actual_hours)

    conn.close()
    click.echo(json.dumps({"ok": True, "ticket": ticket_data}))


@cli.group()
def prov():
    """Manage symbol provenance (capture, show full context)."""
    pass


@prov.command("capture")
@click.option("--symbol-id", type=int, required=True, help="Symbol ID")
@click.option("--spec-id", help="Specification ID")
@click.option("--ticket-id", help="Ticket ID")
@click.option("--created-by", help="Agent/user who created this")
@click.option("--creation-prompt", help="Original prompt that generated the code")
@click.option("--design-rationale", help="Why was it implemented this way?")
def prov_capture(symbol_id, spec_id, ticket_id, created_by, creation_prompt, design_rationale):
    """Capture provenance for a symbol."""
    from agentdb.provenance_tracker import ProvenanceTracker

    conn = ensure_db()
    tracker = ProvenanceTracker(conn)

    prov_data = tracker.capture_provenance(
        symbol_id=symbol_id,
        spec_id=spec_id,
        ticket_id=ticket_id,
        created_by=created_by,
        creation_prompt=creation_prompt,
        design_rationale=design_rationale
    )

    conn.close()
    click.echo(json.dumps({"ok": True, "provenance": prov_data}))


@prov.command("show")
@click.option("--symbol-id", type=int, required=True, help="Symbol ID")
def prov_show(symbol_id):
    """Get full creation context for a symbol (for intelligent backfill)."""
    from agentdb.provenance_tracker import ProvenanceTracker

    conn = ensure_db()
    tracker = ProvenanceTracker(conn)

    context = tracker.get_full_context_for_symbol(symbol_id)

    conn.close()
    click.echo(json.dumps({"ok": True, "context": context}))


# ============================================================
# WORKER POOL COMMANDS
# ============================================================

@cli.group()
def pool():
    """Worker pool management (claim, complete, status)."""
    pass


@pool.command("next-task")
@click.option("--worker-id", required=True, help="Worker identifier (e.g., worker-claude-1)")
@click.option("--capabilities", required=True, help="Comma-separated capabilities (e.g., python,agentdb_cli)")
def pool_next_task(worker_id, capabilities):
    """Get next available task for worker based on capabilities.

    Example:
        agentdb pool next-task --worker-id worker-claude-1 --capabilities python,agentdb_cli,symbol_extraction
    """
    from agentdb.worker_pool import WorkerPoolManager

    caps = set(c.strip() for c in capabilities.split(','))

    try:
        pool = WorkerPoolManager()
        task = pool.get_next_task_for_worker(worker_id, caps)

        if task:
            click.echo(json.dumps({
                'ok': True,
                'task': task,
                'message': f"✅ Claimed {task['task_id']}: {task['title']}"
            }, indent=2))
        else:
            click.echo(json.dumps({
                'ok': False,
                'message': 'No available tasks matching capabilities'
            }))
    except FileNotFoundError as e:
        click.echo(json.dumps({'ok': False, 'error': str(e)}))
    except ValueError as e:
        click.echo(json.dumps({'ok': False, 'error': str(e)}))


@pool.command("complete")
@click.option("--task-id", required=True, help="Task ID to complete (e.g., REVIEW-001)")
@click.option("--worker-id", required=True, help="Worker completing the task")
@click.option("--summary", required=True, help="Deliverables summary")
@click.option("--notes", default="", help="Implementation notes (optional)")
def pool_complete(task_id, worker_id, summary, notes):
    """Mark task complete and capture provenance.

    Example:
        agentdb pool complete --task-id REVIEW-001 --worker-id worker-claude-1 \\
            --summary "15 files ingested, 187 symbols extracted" \\
            --notes "Token savings: 96.8%"
    """
    from agentdb.worker_pool import WorkerPoolManager

    try:
        pool = WorkerPoolManager()

        provenance_data = {}
        if notes:
            provenance_data['implementation_notes'] = notes

        task = pool.complete_task(
            task_id,
            worker_id,
            summary,
            provenance_data=provenance_data
        )

        click.echo(json.dumps({
            'ok': True,
            'task': task,
            'message': f"✅ Completed {task_id} in {task.get('actual_hours', 0):.2f} hours"
        }, indent=2))

        if task.get('unblocked_tasks'):
            click.echo(f"\n🔓 Unblocked {task['unblocked_tasks']} dependent task(s)")

    except FileNotFoundError as e:
        click.echo(json.dumps({'ok': False, 'error': str(e)}))
    except ValueError as e:
        click.echo(json.dumps({'ok': False, 'error': str(e)}))


@pool.command("status")
@click.option("--verbose", is_flag=True, help="Show detailed task information")
def pool_status(verbose):
    """Get current pool status (tasks, workers, statistics).

    Example:
        agentdb pool status
        agentdb pool status --verbose
    """
    from agentdb.worker_pool import WorkerPoolManager

    try:
        pool = WorkerPoolManager()
        status = pool.get_pool_status()

        if verbose:
            click.echo(json.dumps(status, indent=2))
        else:
            # Compact view
            stats = status['statistics']
            click.echo("\n📊 Worker Pool Status")
            click.echo("=" * 50)
            click.echo(f"Tasks: {stats['completed']}/{stats['total_tasks']} completed")
            click.echo(f"  • Available: {stats['available']}")
            click.echo(f"  • In Progress: {stats['in_progress']}")
            click.echo(f"  • Blocked: {stats['blocked']}")
            click.echo(f"  • Completed: {stats['completed']}")
            click.echo(f"\nWorkers: {stats['busy_workers']}/{stats['total_workers']} busy")

            if status['tasks_by_status']['in_progress']:
                click.echo("\n🔄 In Progress:")
                for t in status['tasks_by_status']['in_progress']:
                    click.echo(f"  • {t['task_id']}: {t['title']} ({t['assigned_to']})")

            if status['tasks_by_status']['available']:
                click.echo("\n✅ Available:")
                for t in status['tasks_by_status']['available']:
                    click.echo(f"  • {t['task_id']}: {t['title']} [{t['priority']}]")

    except FileNotFoundError as e:
        click.echo(json.dumps({'ok': False, 'error': str(e)}))


@pool.command("list-workers")
def pool_list_workers():
    """List all registered workers and their capabilities.

    Example:
        agentdb pool list-workers
    """
    from agentdb.worker_pool import WorkerPoolManager

    try:
        pool = WorkerPoolManager()
        status = pool.get_pool_status()

        click.echo("\n👷 Registered Workers")
        click.echo("=" * 70)

        for w in status['workers']:
            status_icon = "🔄" if w['status'] == 'busy' else "💤"
            click.echo(f"\n{status_icon} {w['worker_id']} ({w['worker_type']})")
            click.echo(f"   Status: {w['status']}")
            if w['current_task']:
                click.echo(f"   Current: {w['current_task']}")
            click.echo(f"   Completed: {w['tasks_completed']} tasks ({w['total_hours']:.1f}h)")

    except FileNotFoundError as e:
        click.echo(json.dumps({'ok': False, 'error': str(e)}))


def cli_entry():
    cli(prog_name="agentdb")

if __name__ == "__main__":
    cli_entry()

