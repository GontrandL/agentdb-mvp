#!/usr/bin/env python3

Contract injector for AI agent sessions.

Automatically injects CLAUDE.md as system context into agent workflows.
Can generate compressed versions for token-limited scenarios.

Usage:
    # Full contract injection (for Claude Code, etc.)
    python3 scripts/contract_injector.py --mode full

    # Compressed contract (Quick Reference + Invariant Constraints only)
    python3 scripts/contract_injector.py --mode compressed

    # JSON envelope for MCP/API workflows
    python3 scripts/contract_injector.py --mode json --output-format mcp

    # Validate contract integrity before injection
    python3 scripts/contract_injector.py --validate-only

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Dict, Any


class ContractInjector:
    """Manages CLAUDE.md contract injection into agent sessions."""

    def __init__(self, repo_root: pathlib.Path = None):
        if repo_root is None:
            repo_root = pathlib.Path(__file__).parent.parent
        self.repo_root = repo_root
        self.contract_path = repo_root / "CLAUDE.md"
        self.hash_path = repo_root / ".contract_hash"
        self.metadata_path = repo_root / ".contract_metadata.json"

    def validate_contract(self) -> bool:
        """Verify contract exists and matches expected hash."""
        if not self.contract_path.exists():
            print("❌ CLAUDE.md not found!", file=sys.stderr)
            return False

        content = self.contract_path.read_bytes()
        current_hash = hashlib.sha256(content).hexdigest()

        if self.hash_path.exists():
            expected = self.hash_path.read_text().strip()
            if current_hash != expected:
                print(
                    f"⚠️  Contract hash mismatch!\n"
                    f"   Expected: {expected}\n"
                    f"   Current:  {current_hash}",
                    file=sys.stderr,
                )
                return False

        return True

    def get_contract_metadata(self) -> Dict[str, Any]:
        """Load contract metadata."""
        if self.metadata_path.exists():
            return json.loads(self.metadata_path.read_text())

        # Generate minimal metadata
        content = self.contract_path.read_bytes()
        return {
            "contract_hash": f"sha256:{hashlib.sha256(content).hexdigest()}",
            "contract_version": "2025-10-26",
            "system_prompt_compatible": True,
        }

    def extract_section(self, content: str, section_title: str) -> str:
        """Extract a section from CLAUDE.md by title."""
        # Match section header (##) and capture until next ## header (not ###)
        lines = content.split('\n')
        start_idx = None
        end_idx = None

        for i, line in enumerate(lines):
            # Match only ## headers (not ###, ####, etc.)
            if line.startswith('## ') and section_title in line:
                start_idx = i
            elif start_idx is not None and line.startswith('## ') and section_title not in line:
                # Found next major section
                end_idx = i
                break

        if start_idx is not None:
            if end_idx is None:
                end_idx = len(lines)
            return '\n'.join(lines[start_idx:end_idx]).strip()
        return ""

    def generate_full_contract(self) -> str:
        """Return full CLAUDE.md content."""
        return self.contract_path.read_text()

    def generate_compressed_contract(self) -> str:
        """
        Generate compressed version with essential sections only.

        Includes:
        - Quick Reference
        - INVARIANT CONSTRAINTS
        - Pre-Flight Checklist
        - Error Recovery (common errors only)
        """
        content = self.contract_path.read_text()

        sections = [
            "🚀 Quick Reference (Agent Onboarding)",
            "🚨 INVARIANT CONSTRAINTS (NEVER VIOLATE)",
            "✅ Pre-Flight Checklist (Run Before Every Operation)",
        ]

        compressed = ["# CLAUDE.md (Compressed Contract)", ""]
        compressed.append("**⚠️ CONTRACT ANCHOR: Invariant constraints for AI agents.**\n")

        for section in sections:
            extracted = self.extract_section(content, section)
            if extracted:
                compressed.append(extracted)
                compressed.append("")

        # Add abbreviated error recovery
        compressed.append("## 🔧 Common Errors (Quick Reference)")
        compressed.append("")
        compressed.append("- `indexed_file_rejects_full_content` → Use `patch`, not `ingest`")
        compressed.append("- `agtag_missing` → Add AGTAG block at EOF")
        compressed.append("- `hash_conflict` → Get fresh hash via `agentdb inventory`")
        compressed.append("- `no_final_file_in_patch` → Include `AGTAG_PATCH_FINAL_FILE` envelope")
        compressed.append("")
        compressed.append("**Full contract**: CLAUDE.md")

        return "\n".join(compressed)

    def generate_json_envelope(self, contract_mode: str = "full") -> Dict[str, Any]:
        """
        Generate JSON envelope for MCP/API workflows.

        Compatible with AG-CTX v1 specification.
        """
        metadata = self.get_contract_metadata()

        if contract_mode == "compressed":
            contract_text = self.generate_compressed_contract()
        else:
            contract_text = self.generate_full_contract()

        return {
            "role_pack": {
                "role_id": "agentdb_implementer",
                "role_version": metadata.get("contract_version", "2025-10-26"),
                "system_prompt_hash": metadata["contract_hash"],
                "contract_anchor": "CLAUDE.md",
            },
            "system_message": {
                "role": "system",
                "content": (
                    "You are an AI coding agent working with the agentdb-mvp repository. "
                    "The following contract defines invariant constraints you MUST follow. "
                    "Violations will cause command failures.\n\n"
                    f"{contract_text}"
                ),
            },
            "metadata": metadata,
        }

    def inject_for_claude_code(self, mode: str = "full") -> str:
        """
        Format contract for Claude Code injection.

        Returns markdown-formatted system message.
        """
        if mode == "compressed":
            contract = self.generate_compressed_contract()
        else:
            contract = self.generate_full_contract()

        metadata = self.get_contract_metadata()

        preamble = [
            "# Agent Session Contract",
            "",
            f"**Contract Version**: {metadata.get('contract_version', 'unknown')}",
            f"**Contract Hash**: {metadata['contract_hash']}",
            "",
            "You are working in the `agentdb-mvp` repository. "
            "The following rules are **invariant constraints** enforced by the system.",
            "",
            "---",
            "",
        ]

        return "\n".join(preamble) + contract

    def save_compressed_contract(self, output_path: pathlib.Path = None):
        """Save compressed contract to disk."""
        if output_path is None:
            output_path = self.repo_root / "CLAUDE.min.md"

        compressed = self.generate_compressed_contract()
        output_path.write_text(compressed)
        print(f"✓ Compressed contract saved: {output_path}")


def contract_diff(base_ref: str = "HEAD~1", target_ref: str = "HEAD") -> str:
    """
    Generate diff between two contract versions.

    Args:
        base_ref: Git reference for base version (default: HEAD~1)
        target_ref: Git reference for target version (default: HEAD)

    Returns:
        Human-readable diff report
    """
    import subprocess

    try:
        # Get contract content at base ref
        base_cmd = ["git", "show", f"{base_ref}:CLAUDE.md"]
        base_result = subprocess.run(base_cmd, capture_output=True, text=True, check=True)
        base_content = base_result.stdout

        # Get contract content at target ref
        target_cmd = ["git", "show", f"{target_ref}:CLAUDE.md"]
        target_result = subprocess.run(target_cmd, capture_output=True, text=True, check=True)
        target_content = target_result.stdout

        # Calculate hashes
        base_hash = hashlib.sha256(base_content.encode()).hexdigest()
        target_hash = hashlib.sha256(target_content.encode()).hexdigest()

        # Generate unified diff
        import difflib
        diff_lines = list(difflib.unified_diff(
            base_content.splitlines(keepends=True),
            target_content.splitlines(keepends=True),
            fromfile=f"CLAUDE.md@{base_ref}",
            tofile=f"CLAUDE.md@{target_ref}",
            lineterm=''
        ))

        # Analyze changes
        additions = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
        deletions = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))

        # Check for changes in critical sections
        critical_sections = [
            "INVARIANT CONSTRAINTS",
            "Rule 1:",
            "Rule 2:",
            "Rule 3:",
            "Rule 4:",
            "Rule 5:"
        ]

        critical_changes = []
        for section in critical_sections:
            for line in diff_lines:
                if section in line and (line.startswith('+') or line.startswith('-')):
                    critical_changes.append(section)
                    break

        # Build report
        report = [
            "# Contract Diff Report",
            "",
            f"**Base:**    {base_ref} (sha256:{base_hash[:16]}...)",
            f"**Target:**  {target_ref} (sha256:{target_hash[:16]}...)",
            "",
            "## Change Summary",
            f"- Lines added: {additions}",
            f"- Lines deleted: {deletions}",
            f"- Net change: {additions - deletions:+d}",
            "",
        ]

        if base_hash == target_hash:
            report.append("✅ **No changes detected**")
        else:
            report.append("⚠️ **Contract has changed**")

        if critical_changes:
            report.extend([
                "",
                "## 🚨 Critical Section Changes",
                "",
                "The following critical sections were modified:",
            ])
            for section in set(critical_changes):
                report.append(f"- {section}")
            report.extend([
                "",
                "**Action Required:**",
                "1. Review changes carefully",
                "2. Update contract_version if breaking",
                "3. Run `make contract-update`",
                "4. Test all agent workflows",
            ])

        report.extend([
            "",
            "## Detailed Diff",
            "",
            "```diff"
        ])
        report.extend(diff_lines)
        report.append("```")

        return "\n".join(report)

    except subprocess.CalledProcessError as e:
        return f"Error: Could not retrieve contract at {e.cmd[2]}\n{e.stderr}"
    except Exception as e:
        return f"Error generating diff: {str(e)}"


def main():
    parser = argparse.ArgumentParser(
        description="Inject CLAUDE.md contract into agent sessions"
    )
    parser.add_argument(
        "--mode",
        choices=["full", "compressed"],
        default="full",
        help="Contract injection mode (default: full)",
    )
    parser.add_argument(
        "--output-format",
        choices=["text", "json", "mcp"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate contract integrity, don't inject",
    )
    parser.add_argument(
        "--save-compressed",
        action="store_true",
        help="Save compressed contract to CLAUDE.min.md",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Show diff between contract versions",
    )
    parser.add_argument(
        "--base-ref",
        default="HEAD~1",
        help="Base git reference for diff (default: HEAD~1)",
    )
    parser.add_argument(
        "--target-ref",
        default="HEAD",
        help="Target git reference for diff (default: HEAD)",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        help="Output file path (default: stdout)",
    )

    args = parser.parse_args()

    injector = ContractInjector()

    # Show diff between versions
    if args.diff:
        diff_report = contract_diff(args.base_ref, args.target_ref)
        if args.output:
            args.output.write_text(diff_report)
            print(f"✓ Diff report saved: {args.output}")
        else:
            print(diff_report)
        return

    # Validate contract
    if not injector.validate_contract():
        sys.exit(1)

    if args.validate_only:
        print("✅ Contract validation passed")
        metadata = injector.get_contract_metadata()
        print(f"   Hash: {metadata['contract_hash']}")
        print(f"   Version: {metadata.get('contract_version', 'unknown')}")
        return

    # Save compressed version
    if args.save_compressed:
        injector.save_compressed_contract()
        return

    # Generate output
    if args.output_format == "json" or args.output_format == "mcp":
        output = json.dumps(
            injector.generate_json_envelope(args.mode), indent=2
        )
    else:
        output = injector.inject_for_claude_code(args.mode)

    # Write output
    if args.output:
        args.output.write_text(output)
        print(f"✓ Contract injected: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()


<!--AGTAG v1 START-->
{
  "version": "v1",
  "symbols": [
    {
      "name": "ContractInjector",
      "kind": "class",
      "signature": "class ContractInjector",
      "lines": [
        30,
        208
      ],
      "summary_l0": "Class ContractInjector",
      "contract_l1": "See source code"
    },
    {
      "name": "contract_diff",
      "kind": "function",
      "signature": "def contract_diff(...)",
      "lines": [
        211,
        321
      ],
      "summary_l0": "Function contract_diff",
      "contract_l1": "@io see source code"
    },
    {
      "name": "main",
      "kind": "function",
      "signature": "def main(...)",
      "lines": [
        324,
        414
      ],
      "summary_l0": "Function main",
      "contract_l1": "@io see source code"
    },
    {
      "name": "__init__",
      "kind": "function",
      "signature": "def __init__(...)",
      "lines": [
        33,
        39
      ],
      "summary_l0": "Function __init__",
      "contract_l1": "@io see source code"
    },
    {
      "name": "validate_contract",
      "kind": "function",
      "signature": "def validate_contract(...)",
      "lines": [
        41,
        61
      ],
      "summary_l0": "Function validate_contract",
      "contract_l1": "@io see source code"
    },
    {
      "name": "get_contract_metadata",
      "kind": "function",
      "signature": "def get_contract_metadata(...)",
      "lines": [
        63,
        74
      ],
      "summary_l0": "Function get_contract_metadata",
      "contract_l1": "@io see source code"
    },
    {
      "name": "extract_section",
      "kind": "function",
      "signature": "def extract_section(...)",
      "lines": [
        76,
        96
      ],
      "summary_l0": "Function extract_section",
      "contract_l1": "@io see source code"
    },
    {
      "name": "generate_full_contract",
      "kind": "function",
      "signature": "def generate_full_contract(...)",
      "lines": [
        98,
        100
      ],
      "summary_l0": "Function generate_full_contract",
      "contract_l1": "@io see source code"
    },
    {
      "name": "generate_compressed_contract",
      "kind": "function",
      "signature": "def generate_compressed_contract(...)",
      "lines": [
        102,
        139
      ],
      "summary_l0": "Function generate_compressed_contract",
      "contract_l1": "@io see source code"
    },
    {
      "name": "generate_json_envelope",
      "kind": "function",
      "signature": "def generate_json_envelope(...)",
      "lines": [
        141,
        171
      ],
      "summary_l0": "Function generate_json_envelope",
      "contract_l1": "@io see source code"
    },
    {
      "name": "inject_for_claude_code",
      "kind": "function",
      "signature": "def inject_for_claude_code(...)",
      "lines": [
        173,
        199
      ],
      "summary_l0": "Function inject_for_claude_code",
      "contract_l1": "@io see source code"
    },
    {
      "name": "save_compressed_contract",
      "kind": "function",
      "signature": "def save_compressed_contract(...)",
      "lines": [
        201,
        208
      ],
      "summary_l0": "Function save_compressed_contract",
      "contract_l1": "@io see source code"
    }
  ]
}
<!--AGTAG v1 END-->
