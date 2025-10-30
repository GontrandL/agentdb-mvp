"""
Contract anchor validation tests.

Ensures CLAUDE.md hasn't been modified without explicit version bump.
This prevents accidental drift in agent behavior contracts.
"""
import hashlib
import pathlib
import json


def test_claude_contract_hash():
    """Verify CLAUDE.md matches expected hash."""
    contract_path = pathlib.Path(__file__).parent.parent / "CLAUDE.md"
    hash_file = pathlib.Path(__file__).parent.parent / ".contract_hash"

    if not contract_path.exists():
        raise FileNotFoundError("CLAUDE.md not found — contract anchor missing!")

    # Calculate current hash
    content = contract_path.read_bytes()
    current_digest = hashlib.sha256(content).hexdigest()

    # Check against stored hash (if exists)
    if hash_file.exists():
        expected = hash_file.read_text().strip()

        if current_digest != expected:
            raise AssertionError(
                f"CLAUDE.md contract has changed!\n"
                f"  Expected: {expected}\n"
                f"  Current:  {current_digest}\n\n"
                f"If this change is intentional:\n"
                f"  1. Review the changes carefully\n"
                f"  2. Update .contract_hash: echo '{current_digest}' > .contract_hash\n"
                f"  3. Document the contract version in CHANGELOG or commit message\n"
                f"  4. Re-test all agent workflows\n"
            )
    else:
        # First run — store the hash
        hash_file.write_text(current_digest + "\n")
        print(f"✓ Initial contract hash stored: {current_digest}")


def test_contract_structure():
    """Verify CLAUDE.md contains all required sections."""
    contract_path = pathlib.Path(__file__).parent.parent / "CLAUDE.md"
    content = contract_path.read_text()

    required_sections = [
        "CONTRACT ANCHOR",
        "Quick Reference",
        "INVARIANT CONSTRAINTS",
        "Rule 1: File State Contract",
        "Rule 2: AGTAG Block Requirements",
        "Rule 3: Handle Format",
        "Rule 4: Patch Envelope Format",
        "Rule 5: Context-First Strategy",
        "Pre-Flight Checklist",
        "Error Recovery & Troubleshooting",
    ]

    missing = []
    for section in required_sections:
        if section not in content:
            missing.append(section)

    if missing:
        raise AssertionError(
            f"CLAUDE.md missing required sections:\n" +
            "\n".join(f"  - {s}" for s in missing)
        )


def test_contract_metadata():
    """Generate contract metadata for agent introspection."""
    contract_path = pathlib.Path(__file__).parent.parent / "CLAUDE.md"
    content = contract_path.read_bytes()

    metadata = {
        "contract_file": "CLAUDE.md",
        "contract_hash": f"sha256:{hashlib.sha256(content).hexdigest()}",
        "contract_size_bytes": len(content),
        "contract_version": "2025-10-26",  # Update when contract changes
        "enforcement_points": [
            "schema.sql:8 (db_state CHECK constraint)",
            "core.py:122 (indexed_file_rejects_full_content)",
            "core.py:127-128 (agtag_missing)",
            "core.py:202-204 (hash_conflict)",
            "core.py:217-218 (no_final_file_in_patch)",
        ],
        "system_prompt_compatible": True,
        "mcp_discoverable": True,
    }

    # Write metadata for MCP/agent introspection
    metadata_path = pathlib.Path(__file__).parent.parent / ".contract_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))

    print(f"✓ Contract metadata: {metadata['contract_hash']}")


def test_invariant_rules_present():
    """Verify all 5 invariant rules are documented with enforcement."""
    contract_path = pathlib.Path(__file__).parent.parent / "CLAUDE.md"
    content = contract_path.read_text()

    rules = [
        ("Rule 1", "core.py:122"),  # File state contract enforcement
        ("Rule 2", "core.py:127"),  # AGTAG validation
        ("Rule 3", "core.py:141"),  # Handle format parsing
        ("Rule 4", "core.py:217"),  # Patch envelope requirement
        ("Rule 5", "MANDATORY WORKFLOW"),  # Context-first strategy
    ]

    for rule_name, enforcement_ref in rules:
        if rule_name not in content:
            raise AssertionError(f"Missing {rule_name} in INVARIANT CONSTRAINTS")

        # Rule 5 is behavioral, others have code refs
        if "core.py" in enforcement_ref and enforcement_ref not in content:
            raise AssertionError(
                f"{rule_name} missing enforcement reference: {enforcement_ref}"
            )


if __name__ == "__main__":
    # Run tests
    test_claude_contract_hash()
    test_contract_structure()
    test_contract_metadata()
    test_invariant_rules_present()
    print("\n✅ All contract validation tests passed!")

AGTAG_METADATA = """

<!--AGTAG v1 START-->
{
  "version": "v1",
  "symbols": [
    {
      "name": "test_claude_contract_hash",
      "kind": "function",
      "qualified_name": "tests.test_contract_anchor.test_claude_contract_hash",
      "lines": [
        12,
        42
      ],
      "summary_l0": "Pytest case test_claude_contract_hash validating expected behaviour.",
      "contract_l1": "def test_claude_contract_hash()",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_contract_anchor.py"
    },
    {
      "name": "test_contract_structure",
      "kind": "function",
      "qualified_name": "tests.test_contract_anchor.test_contract_structure",
      "lines": [
        45,
        72
      ],
      "summary_l0": "Pytest case test_contract_structure validating expected behaviour.",
      "contract_l1": "def test_contract_structure()",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_contract_anchor.py"
    },
    {
      "name": "test_contract_metadata",
      "kind": "function",
      "qualified_name": "tests.test_contract_anchor.test_contract_metadata",
      "lines": [
        75,
        100
      ],
      "summary_l0": "Pytest case test_contract_metadata validating expected behaviour.",
      "contract_l1": "def test_contract_metadata()",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_contract_anchor.py"
    },
    {
      "name": "test_invariant_rules_present",
      "kind": "function",
      "qualified_name": "tests.test_contract_anchor.test_invariant_rules_present",
      "lines": [
        103,
        124
      ],
      "summary_l0": "Pytest case test_invariant_rules_present validating expected behaviour.",
      "contract_l1": "def test_invariant_rules_present()",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_contract_anchor.py"
    }
  ],
  "tests": [
    {
      "path": "tests/test_contract_anchor.py",
      "name": "tests.test_contract_anchor.test_claude_contract_hash",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_contract_anchor.py",
      "name": "tests.test_contract_anchor.test_contract_structure",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_contract_anchor.py",
      "name": "tests.test_contract_anchor.test_contract_metadata",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_contract_anchor.py",
      "name": "tests.test_contract_anchor.test_invariant_rules_present",
      "covers": [],
      "status": "new"
    }
  ]
}
<!--AGTAG v1 END-->
"""
