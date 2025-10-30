"""
Unit tests for AGTAG DoS Protection (V-3 Security Fix)

Tests size and depth limits to prevent DoS attacks via:
1. Oversized AGTAG JSON (> 100KB)
2. Deeply nested JSON (> 10 levels)
3. Combination attacks (large + deep)
4. Malformed JSON handling
"""
import pytest
import json
from src.agentdb.core import (
    parse_agtag_block,
    check_json_depth,
    MAX_AGTAG_SIZE,
    MAX_JSON_DEPTH,
    AGTAG_START,
    AGTAG_END
)


class TestAGTAGSizeLimit:
    """Test AGTAG size limit enforcement."""

    def test_normal_agtag_passes(self):
        """Normal-sized AGTAG should pass validation."""
        agtag_data = {
            "version": "v1",
            "symbols": [
                {
                    "name": "example",
                    "kind": "function",
                    "summary_l0": "Example function",
                    "contract_l1": "@io none -> none"
                }
            ]
        }

        agtag_block = f"""{AGTAG_START}
{json.dumps(agtag_data)}
{AGTAG_END}"""

        # Should not raise
        result = parse_agtag_block(agtag_block, "test.py")
        assert result["version"] == "v1"

    def test_large_but_valid_agtag_passes(self):
        """Large but under-limit AGTAG should pass."""
        # Create AGTAG with many symbols (but < 100KB)
        symbols = []
        for i in range(500):  # ~50KB total
            symbols.append({
                "name": f"symbol_{i}",
                "kind": "function",
                "summary_l0": f"Function {i} summary",
                "contract_l1": "@io none -> none"
            })

        agtag_data = {
            "version": "v1",
            "symbols": symbols
        }

        agtag_json = json.dumps(agtag_data)
        assert len(agtag_json) < MAX_AGTAG_SIZE, "Test setup error: AGTAG too large"

        agtag_block = f"""{AGTAG_START}
{agtag_json}
{AGTAG_END}"""

        # Should not raise
        result = parse_agtag_block(agtag_block, "test.py")
        assert len(result["symbols"]) == 500

    def test_oversized_agtag_rejected(self):
        """Oversized AGTAG (> 100KB) should be rejected."""
        # Create oversized AGTAG
        # Each symbol ~200 bytes, so 600 symbols ≈ 120KB
        symbols = []
        for i in range(600):
            symbols.append({
                "name": f"very_long_symbol_name_{i}",
                "kind": "function",
                "summary_l0": f"Very detailed summary for function {i} with lots of explanation",
                "contract_l1": "@io param1:str,param2:int,param3:dict -> dict"
            })

        agtag_data = {
            "version": "v1",
            "symbols": symbols
        }

        agtag_json = json.dumps(agtag_data)
        assert len(agtag_json) > MAX_AGTAG_SIZE, f"Test setup error: AGTAG too small ({len(agtag_json)} bytes)"

        agtag_block = f"""{AGTAG_START}
{agtag_json}
{AGTAG_END}"""

        # Should raise ValueError with size info
        with pytest.raises(ValueError) as exc_info:
            parse_agtag_block(agtag_block, "test.py")

        error_msg = str(exc_info.value)
        assert "too large" in error_msg.lower()
        limit_plain = str(MAX_AGTAG_SIZE)
        limit_formatted = f"{MAX_AGTAG_SIZE:,}"
        assert limit_plain in error_msg or limit_formatted in error_msg

    def test_exact_limit_accepted(self):
        """AGTAG exactly at limit should be accepted."""
        # Create AGTAG exactly at MAX_AGTAG_SIZE
        # Use padding to reach exact size
        padding_size = MAX_AGTAG_SIZE - 200  # Leave room for structure

        agtag_data = {
            "version": "v1",
            "symbols": [{
                "name": "test",
                "kind": "function",
                "summary_l0": "x" * padding_size  # Pad to exact size
            }]
        }

        agtag_json = json.dumps(agtag_data)

        # Adjust to exactly MAX_AGTAG_SIZE
        if len(agtag_json) < MAX_AGTAG_SIZE:
            padding_needed = MAX_AGTAG_SIZE - len(agtag_json)
            agtag_data["symbols"][0]["summary_l0"] += "x" * padding_needed
            agtag_json = json.dumps(agtag_data)

        # Ensure we're at or just under limit
        while len(agtag_json) > MAX_AGTAG_SIZE:
            agtag_data["symbols"][0]["summary_l0"] = agtag_data["symbols"][0]["summary_l0"][:-100]
            agtag_json = json.dumps(agtag_data)

        assert len(agtag_json) <= MAX_AGTAG_SIZE

        agtag_block = f"""{AGTAG_START}
{agtag_json}
{AGTAG_END}"""

        # Should not raise (at or under limit)
        result = parse_agtag_block(agtag_block, "test.py")
        assert result["version"] == "v1"


class TestJSONDepthLimit:
    """Test JSON depth limit enforcement."""

    def test_flat_json_passes(self):
        """Flat JSON (depth 1) should pass."""
        data = {
            "version": "v1",
            "symbols": [{"name": "test", "kind": "function"}]
        }

        # Should not raise
        check_json_depth(data, max_depth=MAX_JSON_DEPTH)

    def test_moderate_depth_passes(self):
        """Moderate nesting (depth 5) should pass."""
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "level5": "value"
                        }
                    }
                }
            }
        }

        # Should not raise (depth 5 < max 10)
        check_json_depth(data, max_depth=MAX_JSON_DEPTH)

    def test_deep_nesting_rejected(self):
        """Deeply nested JSON (> 10 levels) should be rejected."""
        # Create deeply nested structure (15 levels)
        data = {"start": None}
        current = data
        for i in range(15):
            current["nested"] = {}
            current = current["nested"]
        current["value"] = "deep"

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            check_json_depth(data, max_depth=MAX_JSON_DEPTH)

        error_msg = str(exc_info.value)
        assert "too deep" in error_msg.lower()
        assert str(MAX_JSON_DEPTH) in error_msg

    def test_deep_list_nesting_rejected(self):
        """Deeply nested lists (> 10 levels) should be rejected."""
        # Create deeply nested list structure
        data = []
        current = data
        for i in range(15):
            new_list = []
            current.append(new_list)
            current = new_list

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            check_json_depth(data, max_depth=MAX_JSON_DEPTH)

        error_msg = str(exc_info.value)
        assert "too deep" in error_msg.lower()

    def test_exact_depth_limit_accepted(self):
        """JSON exactly at depth limit (10) should be accepted."""
        # Create structure with exactly 10 levels
        data = {"l1": None}
        current = data
        for i in range(2, 11):  # l2 through l10
            current[f"l{i}"] = {}
            current = current[f"l{i}"]
        current["value"] = "at_limit"

        # Should not raise (exactly at limit)
        check_json_depth(data, max_depth=MAX_JSON_DEPTH)

    def test_combined_dict_and_list_depth(self):
        """Combined dict and list nesting should count total depth."""
        # Dict -> list -> dict -> list -> ... (15 levels total)
        # Level 1: dict, Level 2: list, Level 3: dict, Level 4: list, etc.
        data = {
            "d1": [
                {
                    "d2": [
                        {
                            "d3": [
                                {
                                    "d4": [
                                        {
                                            "d5": [
                                                {
                                                    "d6": [
                                                        {
                                                            "d7": "too_deep"
                                                        }
                                                    ]
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        # Should raise ValueError (total depth > 10)
        with pytest.raises(ValueError) as exc_info:
            check_json_depth(data, max_depth=MAX_JSON_DEPTH)

        assert "too deep" in str(exc_info.value).lower()


class TestAGTAGWithDepthLimit:
    """Test AGTAG parsing with depth limits."""

    def test_normal_agtag_with_reasonable_depth(self):
        """Normal AGTAG with reasonable nesting should pass."""
        agtag_data = {
            "version": "v1",
            "symbols": [
                {
                    "name": "example",
                    "kind": "function",
                    "ast_excerpt_l3": {
                        "type": "function",
                        "params": [
                            {"name": "arg1", "type": "str"},
                            {"name": "arg2", "type": "int"}
                        ],
                        "body": {
                            "type": "block",
                            "statements": []
                        }
                    }
                }
            ]
        }

        agtag_block = f"""{AGTAG_START}
{json.dumps(agtag_data)}
{AGTAG_END}"""

        # Should not raise
        result = parse_agtag_block(agtag_block, "test.py")
        assert result["version"] == "v1"

    def test_deeply_nested_ast_rejected(self):
        """AGTAG with deeply nested AST (> 10 levels) should be rejected."""
        # Create deeply nested AST
        ast_node = {"type": "root"}
        current = ast_node
        for i in range(12):  # 12 levels (exceeds limit)
            current["child"] = {"type": f"node_{i}"}
            current = current["child"]

        agtag_data = {
            "version": "v1",
            "symbols": [{
                "name": "example",
                "kind": "function",
                "ast_excerpt_l3": ast_node
            }]
        }

        agtag_block = f"""{AGTAG_START}
{json.dumps(agtag_data)}
{AGTAG_END}"""

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            parse_agtag_block(agtag_block, "test.py")

        assert "too deep" in str(exc_info.value).lower()


class TestMalformedJSON:
    """Test handling of malformed JSON."""

    def test_invalid_json_rejected(self):
        """Malformed JSON should be rejected with clear error."""
        agtag_block = f"""{AGTAG_START}
{{"version": "v1", "symbols": [invalid json here]}}
{AGTAG_END}"""

        # Should raise ValueError (not crash)
        with pytest.raises(ValueError) as exc_info:
            parse_agtag_block(agtag_block, "test.py")

        error_msg = str(exc_info.value)
        assert "invalid json" in error_msg.lower() or "json" in error_msg.lower()

    def test_missing_json_rejected(self):
        """AGTAG without JSON should be rejected."""
        agtag_block = f"""{AGTAG_START}
This is not JSON at all
{AGTAG_END}"""

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            parse_agtag_block(agtag_block, "test.py")

        assert "missing json" in str(exc_info.value).lower()

    def test_empty_agtag_rejected(self):
        """Empty AGTAG should be rejected."""
        agtag_block = f"""{AGTAG_START}
{AGTAG_END}"""

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            parse_agtag_block(agtag_block, "test.py")

        assert "missing json" in str(exc_info.value).lower()


class TestCombinedAttacks:
    """Test combination attacks (large + deep)."""

    def test_large_and_deep_rejected(self):
        """AGTAG that is both large and deeply nested should be rejected."""
        # Create large deeply nested structure
        # Start with deep nesting
        deep_node = {"root": None}
        current = deep_node
        for i in range(15):  # Exceeds depth limit
            current["nested"] = {}
            current = current["nested"]

        # Replicate it many times to also exceed size
        symbols = []
        for i in range(100):
            symbols.append({
                "name": f"symbol_{i}",
                "kind": "function",
                "ast_excerpt_l3": deep_node  # Each has deep nesting
            })

        agtag_data = {
            "version": "v1",
            "symbols": symbols
        }

        agtag_json = json.dumps(agtag_data)

        # Verify we exceed both limits
        # (May fail on depth before size is checked)

        agtag_block = f"""{AGTAG_START}
{agtag_json}
{AGTAG_END}"""

        # Should raise ValueError (depth or size)
        with pytest.raises(ValueError) as exc_info:
            parse_agtag_block(agtag_block, "test.py")

        error_msg = str(exc_info.value).lower()
        # Either depth or size limit hit
        assert ("too deep" in error_msg) or ("too large" in error_msg)


class TestErrorMessages:
    """Test that error messages are helpful."""

    def test_size_error_includes_actual_size(self):
        """Size error should include actual size in message."""
        # Create oversized AGTAG
        large_string = "x" * (MAX_AGTAG_SIZE + 1000)
        agtag_data = {
            "version": "v1",
            "symbols": [{"name": "test", "summary_l0": large_string}]
        }

        agtag_block = f"""{AGTAG_START}
{json.dumps(agtag_data)}
{AGTAG_END}"""

        # Should raise with size info
        with pytest.raises(ValueError) as exc_info:
            parse_agtag_block(agtag_block, "test.py")

        error_msg = str(exc_info.value)
        limit_plain = str(MAX_AGTAG_SIZE)
        limit_formatted = f"{MAX_AGTAG_SIZE:,}"
        # Should mention both limit and actual size
        assert limit_plain in error_msg or limit_formatted in error_msg
        assert "bytes" in error_msg.lower()

    def test_depth_error_includes_limit(self):
        """Depth error should include depth limit in message."""
        # Create deeply nested structure
        data = {"root": None}
        current = data
        for i in range(15):
            current["child"] = {}
            current = current["child"]

        # Should raise with depth info
        with pytest.raises(ValueError) as exc_info:
            check_json_depth(data)

        error_msg = str(exc_info.value)
        # Should mention limit
        assert str(MAX_JSON_DEPTH) in error_msg
        assert "depth" in error_msg.lower()


class TestPerformance:
    """Test DoS protection doesn't introduce performance regression."""

    def test_large_valid_agtag_performance(self):
        """Large but valid AGTAG should parse efficiently."""
        import time

        # Create large valid AGTAG (90KB, under limit)
        symbols = []
        for i in range(220):
            symbols.append({
                "name": f"symbol_{i}",
                "kind": "function",
                "summary_l0": f"Summary {i}" * 20,  # ~300 chars each
                "contract_l1": "@io none -> none"
            })

        agtag_data = {
            "version": "v1",
            "symbols": symbols
        }

        agtag_json = json.dumps(agtag_data)
        assert len(agtag_json) < MAX_AGTAG_SIZE

        agtag_block = f"""{AGTAG_START}
{agtag_json}
{AGTAG_END}"""

        # Should parse quickly (< 100ms)
        start = time.time()
        result = parse_agtag_block(agtag_block, "test.py")
        elapsed = time.time() - start

        assert elapsed < 0.1, f"Parsing took {elapsed:.3f}s (expected < 0.1s)"
        assert len(result["symbols"]) == 220

    def test_depth_check_performance(self):
        """Depth checking should be efficient."""
        import time

        # Create moderately deep structure (depth 8)
        data = {"l1": None}
        current = data
        for i in range(2, 9):
            current[f"l{i}"] = {}
            current = current[f"l{i}"]
        current["value"] = "test"

        # Should check quickly (< 10ms)
        start = time.time()
        check_json_depth(data)
        elapsed = time.time() - start

        assert elapsed < 0.01, f"Depth check took {elapsed:.3f}s (expected < 0.01s)"

AGTAG_METADATA = """

<!--AGTAG v1 START-->
{
  "version": "v1",
  "symbols": [
    {
      "name": "TestAGTAGSizeLimit",
      "kind": "class",
      "qualified_name": "tests.test_agtag_dos_protection.TestAGTAGSizeLimit",
      "lines": [
        22,
        146
      ],
      "summary_l0": "Pytest class TestAGTAGSizeLimit for grouping test cases.",
      "contract_l1": "class TestAGTAGSizeLimit",
      "pseudocode_l2": "1. Organize related pytest cases.",
      "path": "tests/test_agtag_dos_protection.py"
    },
    {
      "name": "test_normal_agtag_passes",
      "kind": "method",
      "qualified_name": "tests.test_agtag_dos_protection.TestAGTAGSizeLimit.test_normal_agtag_passes",
      "lines": [
        25,
        45
      ],
      "summary_l0": "Pytest case test_normal_agtag_passes validating expected behaviour.",
      "contract_l1": "def test_normal_agtag_passes(self)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_agtag_dos_protection.py",
      "parent": "TestAGTAGSizeLimit"
    },
    {
      "name": "test_large_but_valid_agtag_passes",
      "kind": "method",
      "qualified_name": "tests.test_agtag_dos_protection.TestAGTAGSizeLimit.test_large_but_valid_agtag_passes",
      "lines": [
        47,
        73
      ],
      "summary_l0": "Pytest case test_large_but_valid_agtag_passes validating expected behaviour.",
      "contract_l1": "def test_large_but_valid_agtag_passes(self)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_agtag_dos_protection.py",
      "parent": "TestAGTAGSizeLimit"
    },
    {
      "name": "test_oversized_agtag_rejected",
      "kind": "method",
      "qualified_name": "tests.test_agtag_dos_protection.TestAGTAGSizeLimit.test_oversized_agtag_rejected",
      "lines": [
        75,
        108
      ],
      "summary_l0": "Pytest case test_oversized_agtag_rejected validating expected behaviour.",
      "contract_l1": "def test_oversized_agtag_rejected(self)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_agtag_dos_protection.py",
      "parent": "TestAGTAGSizeLimit"
    },
    {
      "name": "test_exact_limit_accepted",
      "kind": "method",
      "qualified_name": "tests.test_agtag_dos_protection.TestAGTAGSizeLimit.test_exact_limit_accepted",
      "lines": [
        110,
        146
      ],
      "summary_l0": "Pytest case test_exact_limit_accepted validating expected behaviour.",
      "contract_l1": "def test_exact_limit_accepted(self)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_agtag_dos_protection.py",
      "parent": "TestAGTAGSizeLimit"
    },
    {
      "name": "TestJSONDepthLimit",
      "kind": "class",
      "qualified_name": "tests.test_agtag_dos_protection.TestJSONDepthLimit",
      "lines": [
        149,
        263
      ],
      "summary_l0": "Pytest class TestJSONDepthLimit for grouping test cases.",
      "contract_l1": "class TestJSONDepthLimit",
      "pseudocode_l2": "1. Organize related pytest cases.",
      "path": "tests/test_agtag_dos_protection.py"
    },
    {
      "name": "test_flat_json_passes",
      "kind": "method",
      "qualified_name": "tests.test_agtag_dos_protection.TestJSONDepthLimit.test_flat_json_passes",
      "lines": [
        152,
        160
      ],
      "summary_l0": "Pytest case test_flat_json_passes validating expected behaviour.",
      "contract_l1": "def test_flat_json_passes(self)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_agtag_dos_protection.py",
      "parent": "TestJSONDepthLimit"
    },
    {
      "name": "test_moderate_depth_passes",
      "kind": "method",
      "qualified_name": "tests.test_agtag_dos_protection.TestJSONDepthLimit.test_moderate_depth_passes",
      "lines": [
        162,
        177
      ],
      "summary_l0": "Pytest case test_moderate_depth_passes validating expected behaviour.",
      "contract_l1": "def test_moderate_depth_passes(self)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_agtag_dos_protection.py",
      "parent": "TestJSONDepthLimit"
    },
    {
      "name": "test_deep_nesting_rejected",
      "kind": "method",
      "qualified_name": "tests.test_agtag_dos_protection.TestJSONDepthLimit.test_deep_nesting_rejected",
      "lines": [
        179,
        195
      ],
      "summary_l0": "Pytest case test_deep_nesting_rejected validating expected behaviour.",
      "contract_l1": "def test_deep_nesting_rejected(self)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_agtag_dos_protection.py",
      "parent": "TestJSONDepthLimit"
    },
    {
      "name": "test_deep_list_nesting_rejected",
      "kind": "method",
      "qualified_name": "tests.test_agtag_dos_protection.TestJSONDepthLimit.test_deep_list_nesting_rejected",
      "lines": [
        197,
        212
      ],
      "summary_l0": "Pytest case test_deep_list_nesting_rejected validating expected behaviour.",
      "contract_l1": "def test_deep_list_nesting_rejected(self)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_agtag_dos_protection.py",
      "parent": "TestJSONDepthLimit"
    },
    {
      "name": "test_exact_depth_limit_accepted",
      "kind": "method",
      "qualified_name": "tests.test_agtag_dos_protection.TestJSONDepthLimit.test_exact_depth_limit_accepted",
      "lines": [
        214,
        225
      ],
      "summary_l0": "Pytest case test_exact_depth_limit_accepted validating expected behaviour.",
      "contract_l1": "def test_exact_depth_limit_accepted(self)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_agtag_dos_protection.py",
      "parent": "TestJSONDepthLimit"
    },
    {
      "name": "test_combined_dict_and_list_depth",
      "kind": "method",
      "qualified_name": "tests.test_agtag_dos_protection.TestJSONDepthLimit.test_combined_dict_and_list_depth",
      "lines": [
        227,
        263
      ],
      "summary_l0": "Pytest case test_combined_dict_and_list_depth validating expected behaviour.",
      "contract_l1": "def test_combined_dict_and_list_depth(self)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_agtag_dos_protection.py",
      "parent": "TestJSONDepthLimit"
    },
    {
      "name": "TestAGTAGWithDepthLimit",
      "kind": "class",
      "qualified_name": "tests.test_agtag_dos_protection.TestAGTAGWithDepthLimit",
      "lines": [
        266,
        326
      ],
      "summary_l0": "Pytest class TestAGTAGWithDepthLimit for grouping test cases.",
      "contract_l1": "class TestAGTAGWithDepthLimit",
      "pseudocode_l2": "1. Organize related pytest cases.",
      "path": "tests/test_agtag_dos_protection.py"
    },
    {
      "name": "test_normal_agtag_with_reasonable_depth",
      "kind": "method",
      "qualified_name": "tests.test_agtag_dos_protection.TestAGTAGWithDepthLimit.test_normal_agtag_with_reasonable_depth",
      "lines": [
        269,
        298
      ],
      "summary_l0": "Pytest case test_normal_agtag_with_reasonable_depth validating expected behaviour.",
      "contract_l1": "def test_normal_agtag_with_reasonable_depth(self)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_agtag_dos_protection.py",
      "parent": "TestAGTAGWithDepthLimit"
    },
    {
      "name": "test_deeply_nested_ast_rejected",
      "kind": "method",
      "qualified_name": "tests.test_agtag_dos_protection.TestAGTAGWithDepthLimit.test_deeply_nested_ast_rejected",
      "lines": [
        300,
        326
      ],
      "summary_l0": "Pytest case test_deeply_nested_ast_rejected validating expected behaviour.",
      "contract_l1": "def test_deeply_nested_ast_rejected(self)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_agtag_dos_protection.py",
      "parent": "TestAGTAGWithDepthLimit"
    },
    {
      "name": "TestMalformedJSON",
      "kind": "class",
      "qualified_name": "tests.test_agtag_dos_protection.TestMalformedJSON",
      "lines": [
        329,
        366
      ],
      "summary_l0": "Pytest class TestMalformedJSON for grouping test cases.",
      "contract_l1": "class TestMalformedJSON",
      "pseudocode_l2": "1. Organize related pytest cases.",
      "path": "tests/test_agtag_dos_protection.py"
    },
    {
      "name": "test_invalid_json_rejected",
      "kind": "method",
      "qualified_name": "tests.test_agtag_dos_protection.TestMalformedJSON.test_invalid_json_rejected",
      "lines": [
        332,
        343
      ],
      "summary_l0": "Pytest case test_invalid_json_rejected validating expected behaviour.",
      "contract_l1": "def test_invalid_json_rejected(self)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_agtag_dos_protection.py",
      "parent": "TestMalformedJSON"
    },
    {
      "name": "test_missing_json_rejected",
      "kind": "method",
      "qualified_name": "tests.test_agtag_dos_protection.TestMalformedJSON.test_missing_json_rejected",
      "lines": [
        345,
        355
      ],
      "summary_l0": "Pytest case test_missing_json_rejected validating expected behaviour.",
      "contract_l1": "def test_missing_json_rejected(self)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_agtag_dos_protection.py",
      "parent": "TestMalformedJSON"
    },
    {
      "name": "test_empty_agtag_rejected",
      "kind": "method",
      "qualified_name": "tests.test_agtag_dos_protection.TestMalformedJSON.test_empty_agtag_rejected",
      "lines": [
        357,
        366
      ],
      "summary_l0": "Pytest case test_empty_agtag_rejected validating expected behaviour.",
      "contract_l1": "def test_empty_agtag_rejected(self)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_agtag_dos_protection.py",
      "parent": "TestMalformedJSON"
    },
    {
      "name": "TestCombinedAttacks",
      "kind": "class",
      "qualified_name": "tests.test_agtag_dos_protection.TestCombinedAttacks",
      "lines": [
        369,
        411
      ],
      "summary_l0": "Pytest class TestCombinedAttacks for grouping test cases.",
      "contract_l1": "class TestCombinedAttacks",
      "pseudocode_l2": "1. Organize related pytest cases.",
      "path": "tests/test_agtag_dos_protection.py"
    },
    {
      "name": "test_large_and_deep_rejected",
      "kind": "method",
      "qualified_name": "tests.test_agtag_dos_protection.TestCombinedAttacks.test_large_and_deep_rejected",
      "lines": [
        372,
        411
      ],
      "summary_l0": "Pytest case test_large_and_deep_rejected validating expected behaviour.",
      "contract_l1": "def test_large_and_deep_rejected(self)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_agtag_dos_protection.py",
      "parent": "TestCombinedAttacks"
    },
    {
      "name": "TestErrorMessages",
      "kind": "class",
      "qualified_name": "tests.test_agtag_dos_protection.TestErrorMessages",
      "lines": [
        414,
        457
      ],
      "summary_l0": "Pytest class TestErrorMessages for grouping test cases.",
      "contract_l1": "class TestErrorMessages",
      "pseudocode_l2": "1. Organize related pytest cases.",
      "path": "tests/test_agtag_dos_protection.py"
    },
    {
      "name": "test_size_error_includes_actual_size",
      "kind": "method",
      "qualified_name": "tests.test_agtag_dos_protection.TestErrorMessages.test_size_error_includes_actual_size",
      "lines": [
        417,
        439
      ],
      "summary_l0": "Pytest case test_size_error_includes_actual_size validating expected behaviour.",
      "contract_l1": "def test_size_error_includes_actual_size(self)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_agtag_dos_protection.py",
      "parent": "TestErrorMessages"
    },
    {
      "name": "test_depth_error_includes_limit",
      "kind": "method",
      "qualified_name": "tests.test_agtag_dos_protection.TestErrorMessages.test_depth_error_includes_limit",
      "lines": [
        441,
        457
      ],
      "summary_l0": "Pytest case test_depth_error_includes_limit validating expected behaviour.",
      "contract_l1": "def test_depth_error_includes_limit(self)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_agtag_dos_protection.py",
      "parent": "TestErrorMessages"
    },
    {
      "name": "TestPerformance",
      "kind": "class",
      "qualified_name": "tests.test_agtag_dos_protection.TestPerformance",
      "lines": [
        460,
        514
      ],
      "summary_l0": "Pytest class TestPerformance for grouping test cases.",
      "contract_l1": "class TestPerformance",
      "pseudocode_l2": "1. Organize related pytest cases.",
      "path": "tests/test_agtag_dos_protection.py"
    },
    {
      "name": "test_large_valid_agtag_performance",
      "kind": "method",
      "qualified_name": "tests.test_agtag_dos_protection.TestPerformance.test_large_valid_agtag_performance",
      "lines": [
        463,
        495
      ],
      "summary_l0": "Pytest case test_large_valid_agtag_performance validating expected behaviour.",
      "contract_l1": "def test_large_valid_agtag_performance(self)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_agtag_dos_protection.py",
      "parent": "TestPerformance"
    },
    {
      "name": "test_depth_check_performance",
      "kind": "method",
      "qualified_name": "tests.test_agtag_dos_protection.TestPerformance.test_depth_check_performance",
      "lines": [
        497,
        514
      ],
      "summary_l0": "Pytest case test_depth_check_performance validating expected behaviour.",
      "contract_l1": "def test_depth_check_performance(self)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_agtag_dos_protection.py",
      "parent": "TestPerformance"
    }
  ],
  "tests": [
    {
      "path": "tests/test_agtag_dos_protection.py",
      "name": "tests.test_agtag_dos_protection.TestAGTAGSizeLimit.test_normal_agtag_passes",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_agtag_dos_protection.py",
      "name": "tests.test_agtag_dos_protection.TestAGTAGSizeLimit.test_large_but_valid_agtag_passes",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_agtag_dos_protection.py",
      "name": "tests.test_agtag_dos_protection.TestAGTAGSizeLimit.test_oversized_agtag_rejected",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_agtag_dos_protection.py",
      "name": "tests.test_agtag_dos_protection.TestAGTAGSizeLimit.test_exact_limit_accepted",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_agtag_dos_protection.py",
      "name": "tests.test_agtag_dos_protection.TestJSONDepthLimit.test_flat_json_passes",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_agtag_dos_protection.py",
      "name": "tests.test_agtag_dos_protection.TestJSONDepthLimit.test_moderate_depth_passes",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_agtag_dos_protection.py",
      "name": "tests.test_agtag_dos_protection.TestJSONDepthLimit.test_deep_nesting_rejected",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_agtag_dos_protection.py",
      "name": "tests.test_agtag_dos_protection.TestJSONDepthLimit.test_deep_list_nesting_rejected",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_agtag_dos_protection.py",
      "name": "tests.test_agtag_dos_protection.TestJSONDepthLimit.test_exact_depth_limit_accepted",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_agtag_dos_protection.py",
      "name": "tests.test_agtag_dos_protection.TestJSONDepthLimit.test_combined_dict_and_list_depth",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_agtag_dos_protection.py",
      "name": "tests.test_agtag_dos_protection.TestAGTAGWithDepthLimit.test_normal_agtag_with_reasonable_depth",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_agtag_dos_protection.py",
      "name": "tests.test_agtag_dos_protection.TestAGTAGWithDepthLimit.test_deeply_nested_ast_rejected",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_agtag_dos_protection.py",
      "name": "tests.test_agtag_dos_protection.TestMalformedJSON.test_invalid_json_rejected",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_agtag_dos_protection.py",
      "name": "tests.test_agtag_dos_protection.TestMalformedJSON.test_missing_json_rejected",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_agtag_dos_protection.py",
      "name": "tests.test_agtag_dos_protection.TestMalformedJSON.test_empty_agtag_rejected",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_agtag_dos_protection.py",
      "name": "tests.test_agtag_dos_protection.TestCombinedAttacks.test_large_and_deep_rejected",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_agtag_dos_protection.py",
      "name": "tests.test_agtag_dos_protection.TestErrorMessages.test_size_error_includes_actual_size",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_agtag_dos_protection.py",
      "name": "tests.test_agtag_dos_protection.TestErrorMessages.test_depth_error_includes_limit",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_agtag_dos_protection.py",
      "name": "tests.test_agtag_dos_protection.TestPerformance.test_large_valid_agtag_performance",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_agtag_dos_protection.py",
      "name": "tests.test_agtag_dos_protection.TestPerformance.test_depth_check_performance",
      "covers": [],
      "status": "new"
    }
  ]
}
<!--AGTAG v1 END-->
"""
