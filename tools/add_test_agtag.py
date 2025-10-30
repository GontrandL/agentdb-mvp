#!/usr/bin/env python3
"""
Generate AGTAG v1 metadata for Python test files.

This helper scans pytest-style modules, extracts classes and functions,
and appends an `AGTAG_METADATA` triple-quoted block so AgentDB ingestion
does not require manual tagging.
"""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass
class Symbol:
    """Lightweight container describing a symbol extracted from a test module."""

    name: str
    kind: str
    qualified_name: str
    lines: List[int]
    summary_l0: str
    contract_l1: str
    pseudocode_l2: Optional[str]
    path: str
    parent: Optional[str] = None

    def to_json(self) -> dict:
        payload = {
            "name": self.name,
            "kind": self.kind,
            "qualified_name": self.qualified_name,
            "lines": self.lines,
            "summary_l0": self.summary_l0,
            "contract_l1": self.contract_l1,
            "pseudocode_l2": self.pseudocode_l2,
            "path": self.path,
        }
        if self.parent:
            payload["parent"] = self.parent
        return payload


def _make_summary(name: str, kind: str) -> str:
    if kind == "class":
        return f"Pytest class {name} for grouping test cases."
    if name.startswith("test_"):
        return f"Pytest case {name} validating expected behaviour."
    return f"Helper {kind} {name} supporting test utilities."


def _make_contract(node: ast.AST) -> str:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        args = ast.unparse(node.args)
        signature = f"def {node.name}({args})"
        if node.returns:
            signature += f" -> {ast.unparse(node.returns)}"
        return signature
    if isinstance(node, ast.ClassDef):
        bases = [ast.unparse(base) for base in node.bases] if node.bases else []
        if bases:
            return f"class {node.name}({', '.join(bases)})"
        return f"class {node.name}"
    return f"symbol {getattr(node, 'name', '<anonymous>')}"


def _collect_symbols(module_path: Path, root: Path) -> List[Symbol]:
    rel_path = module_path.relative_to(root).as_posix()
    module_name = rel_path[:-3].replace("/", ".")  # strip ".py"
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=rel_path)

    symbols: List[Symbol] = []

    def add_symbol(node: ast.AST, kind: str, parent: Optional[str] = None):
        name = getattr(node, "name")
        start = getattr(node, "lineno", 1)
        end = getattr(node, "end_lineno", start)
        qualified = module_name
        if parent:
            qualified += f".{parent}.{name}"
        else:
            qualified += f".{name}"
        symbols.append(
            Symbol(
                name=name,
                kind=kind,
                qualified_name=qualified,
                lines=[start, end],
                summary_l0=_make_summary(name, kind),
                contract_l1=_make_contract(node),
                pseudocode_l2="1. Execute pytest assertions and validations."
                if kind in {"function", "method"}
                else "1. Organize related pytest cases.",
                path=rel_path,
                parent=parent,
            )
        )

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            add_symbol(node, "function")
        elif isinstance(node, ast.ClassDef):
            add_symbol(node, "class")
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    add_symbol(child, "method", parent=node.name)

    return symbols


def _build_agtag(symbols: Iterable[Symbol]) -> str:
    payload = {
        "version": "v1",
        "symbols": [sym.to_json() for sym in symbols],
    }
    tests = [
        {
            "path": sym.path,
            "name": sym.qualified_name,
            "covers": [],
            "status": "new",
        }
        for sym in symbols
        if sym.kind in {"function", "method"} and sym.name.startswith("test_")
    ]
    if tests:
        payload["tests"] = tests
    agtag_json = json.dumps(payload, indent=2)
    return (
        "\n\nAGTAG_METADATA = \"\"\"\n\n<!--AGTAG v1 START-->\n"
        f"{agtag_json}\n"
        "<!--AGTAG v1 END-->\n\"\"\"\n"
    )


def add_agtag(module_path: Path, root: Path) -> bool:
    if not root.is_absolute():
        root = root.resolve()
    module_path = module_path if module_path.is_absolute() else (root / module_path)
    module_path = module_path.resolve()
    text = module_path.read_text(encoding="utf-8")
    if "\n\n<!--AGTAG v1 START-->" in text:
        return False
    symbols = _collect_symbols(module_path, root)
    if not symbols:
        return False
    agtag_block = _build_agtag(symbols)
    module_path.write_text(text.rstrip() + agtag_block, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Append AGTAG metadata to pytest files.")
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Python test files or directories to process",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root for relative paths (default: cwd)",
    )
    args = parser.parse_args()

    processed = 0
    for path in args.paths:
        if path.is_dir():
            for file_path in sorted(path.rglob("*.py")):
                if add_agtag(file_path, args.root):
                    processed += 1
        elif path.suffix == ".py":
            if add_agtag(path, args.root):
                processed += 1
        else:
            continue

    print(f"Added AGTAG metadata to {processed} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
