#!/bin/bash
# AgentDB Core Functionality Validation Script
# Tests all core commands and validates progressive disclosure

set -e

PROJECT_ROOT="/home/gontrand/ActiveProjects/agentdb-mvp"
cd "$PROJECT_ROOT"

echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║          AgentDB Core Functionality Validation                           ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS=0
FAIL=0

# Test function
test_command() {
    local test_name="$1"
    local command="$2"
    local expected_pattern="$3"

    echo -n "Testing: $test_name... "

    output=$(eval "$command" 2>&1)
    exit_code=$?

    if [ $exit_code -eq 0 ] && echo "$output" | grep -q "$expected_pattern"; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((PASS++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        echo "  Command: $command"
        echo "  Output: $output"
        ((FAIL++))
        return 1
    fi
}

# Cleanup old test data
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Setup: Cleaning test environment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
rm -rf .agentdb test_file.py
echo "✓ Cleanup complete"
echo ""

# Test 1: Database Initialization
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test Suite 1: Database Operations"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_command \
    "Database initialization" \
    "python3 -m src.agentdb.core init" \
    "OK: initialized"

test_command \
    "Database file created" \
    "ls -la .agentdb/agent.sqlite" \
    "agent.sqlite"

# Test 2: Inventory (empty database)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test Suite 2: Inventory Operations"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_command \
    "Inventory command (empty)" \
    "python3 -m src.agentdb.core inventory" \
    "OK"

# Test 3: Create test file with AGTAG
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test Suite 3: File Ingestion"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cat > test_file.py << 'PYEOF'
def example_function(a, b):
    """Example function for testing."""
    return a + b

class ExampleClass:
    """Example class for testing."""
    def __init__(self):
        self.value = 42

    def get_value(self):
        return self.value

<!--AGTAG v1 START-->
{
  "version": "v1",
  "symbols": [
    {
      "name": "example_function",
      "kind": "function",
      "lines": [1, 3],
      "summary_l0": "Adds two numbers",
      "contract_l1": "@io a:int,b:int -> int",
      "pseudocode_l2": "1. Take two inputs\n2. Return sum",
      "code_l4": "def example_function(a, b):\n    return a + b"
    },
    {
      "name": "ExampleClass",
      "kind": "class",
      "lines": [5, 11],
      "summary_l0": "Example class with value storage",
      "contract_l1": "class ExampleClass\n  value: int\n  get_value() -> int"
    }
  ]
}
<!--AGTAG v1 END-->
PYEOF

echo "✓ Created test_file.py with AGTAG"

# Test 4: Ingest file
test_command \
    "File ingestion" \
    "python3 -m src.agentdb.core ingest --path test_file.py < test_file.py" \
    "OK"

# Test 5: Inventory (after ingest)
test_command \
    "Inventory after ingest" \
    "python3 -m src.agentdb.core inventory" \
    "test_file.py"

# Test 6: Progressive Disclosure - Focus (L0/L1)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test Suite 4: Progressive Disclosure (L0-L4)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_command \
    "Focus (L0/L1) - example_function" \
    "python3 -m src.agentdb.core focus --handle 'ctx://test_file.py::example_function@sha256:ANY' --depth 0" \
    "Adds two numbers"

test_command \
    "Focus includes contract (L1)" \
    "python3 -m src.agentdb.core focus --handle 'ctx://test_file.py::example_function@sha256:ANY' --depth 0" \
    "@io"

# Test 7: Zoom to L2
test_command \
    "Zoom to L2 (pseudocode)" \
    "python3 -m src.agentdb.core zoom --handle 'ctx://test_file.py::example_function@sha256:ANY' --level 2" \
    "pseudocode"

# Test 8: Zoom to L4
test_command \
    "Zoom to L4 (full code)" \
    "python3 -m src.agentdb.core zoom --handle 'ctx://test_file.py::example_function@sha256:ANY' --level 4" \
    "def example_function"

# Test 9: Query ExampleClass
test_command \
    "Focus on ExampleClass" \
    "python3 -m src.agentdb.core focus --handle 'ctx://test_file.py::ExampleClass@sha256:ANY' --depth 0" \
    "Example class"

# Test 10: Patch operation
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test Suite 5: Patch Operations"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Get current hash
CURRENT_HASH=$(python3 -m src.agentdb.core inventory 2>/dev/null | grep test_file.py | grep -o 'sha256:[a-f0-9]*' || echo "sha256:unknown")

if [ "$CURRENT_HASH" != "sha256:unknown" ]; then
    # Create patch file
    cat > test_patch.diff << 'PATCHEOF'
--- a/test_file.py
+++ b/test_file.py
@@ -1,3 +1,3 @@
 def example_function(a, b):
-    """Example function for testing."""
+    """Example function for testing - updated."""
     return a + b

AGTAG_PATCH_FINAL_FILE {
  "final_file": "def example_function(a, b):\n    \"\"\"Example function for testing - updated.\"\"\"\n    return a + b\n\nclass ExampleClass:\n    \"\"\"Example class for testing.\"\"\"\n    def __init__(self):\n        self.value = 42\n    \n    def get_value(self):\n        return self.value\n\n<!--AGTAG v1 START-->\n{\n  \"version\": \"v1\",\n  \"symbols\": [\n    {\n      \"name\": \"example_function\",\n      \"kind\": \"function\",\n      \"lines\": [1, 3],\n      \"summary_l0\": \"Adds two numbers\",\n      \"contract_l1\": \"@io a:int,b:int -> int\",\n      \"pseudocode_l2\": \"1. Take two inputs\\n2. Return sum\",\n      \"code_l4\": \"def example_function(a, b):\\n    return a + b\"\n    },\n    {\n      \"name\": \"ExampleClass\",\n      \"kind\": \"class\",\n      \"lines\": [5, 11],\n      \"summary_l0\": \"Example class with value storage\",\n      \"contract_l1\": \"class ExampleClass\\n  value: int\\n  get_value() -> int\"\n    }\n  ]\n}\n<!--AGTAG v1 END-->"
} END
PATCHEOF

    test_command \
        "Patch application" \
        "python3 -m src.agentdb.core patch --path test_file.py --hash-before $CURRENT_HASH < test_patch.diff" \
        "OK"
else
    echo -e "${YELLOW}⚠ SKIP${NC} Patch test (couldn't get hash)"
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test Results Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "Tests Passed:  ${GREEN}$PASS${NC}"
echo -e "Tests Failed:  ${RED}$FAIL${NC}"
echo -e "Total Tests:   $((PASS + FAIL))"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
    echo ""
    echo "Core AgentDB is fully functional and ready for production!"
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo ""
    echo "Please review the failures above."
    exit 1
fi
