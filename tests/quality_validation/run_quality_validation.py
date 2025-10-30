"""
Quality Validation Test Runner

Executes 10 A/B test cases comparing full context vs L0/L1 compression.
Tests cover different query types to validate compression maintains quality.

Usage:
    python run_quality_validation.py
    python run_quality_validation.py --test-case 3  # Run specific test
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.quality_validation.ab_test_context import ContextQualityValidator


def run_test_case_1(validator: ContextQualityValidator):
    """Test Case 1: Factual Retrieval - High similarity expected (>0.98)"""
    print("\n=== Test Case 1: Factual Retrieval ===")

    query = "What are the main components of the AgentDB MVP system?"

    full_context = """
# AgentDB MVP Architecture

## Core Components

1. **Database Layer (SQLite + FTS5)**
   - Files table: Tracks file states (missing/indexed)
   - Symbols table: Stores symbol metadata with L0-L4 levels
   - Edges table: Symbol relationships and dependencies
   - FTS5 virtual table: Full-text search on L0/L1

2. **CLI Interface (core.py)**
   - init: Initialize database
   - ingest: Add files with AGTAG metadata
   - search: FTS5-powered symbol search
   - focus: Context retrieval with depth control
   - zoom: Progressive disclosure (L0-L4)
   - patch: Incremental updates

3. **Progressive Disclosure (L0-L4)**
   - L0: One-line overview
   - L1: Contract (inputs/outputs)
   - L2: Pseudocode algorithm
   - L3: AST excerpt
   - L4: Full source code

4. **Auto-Tagger System**
   - Markdown auto-tagger: Extract headings → L0/L1/L2
   - Python auto-tagger: AST parsing for functions/classes
   - AGTAG v1 format: JSON metadata at EOF
"""

    l0l1_context = """
L0: AgentDB MVP has 4 main components: database layer, CLI interface, progressive disclosure, auto-tagger system
L1: @components database_layer:SQLite, cli:core.py, progressive_disclosure:L0-L4, auto_tagger:markdown+python
"""

    return validator.run_ab_test(
        test_case_id=1,
        query=query,
        full_context=full_context,
        l0l1_context=l0l1_context,
        query_type="factual",
        threshold=0.98
    )


def run_test_case_2(validator: ContextQualityValidator):
    """Test Case 2: Reasoning/Analysis - Medium-high similarity expected (>0.92)"""
    print("\n=== Test Case 2: Reasoning/Analysis ===")

    query = "Should I use L0/L1 or L4 for code generation tasks? Explain your reasoning."

    full_context = """
# Progressive Disclosure Strategy

## When to Use Each Level

### L0/L1 (Overview + Contract)
- **Best for:** Factual queries, decisions, simple lookups
- **Token cost:** ~25 tokens (97.5% savings vs L4)
- **Quality:** Maintains >95% semantic similarity for factual queries
- **Use cases:**
  - "What does this function do?"
  - "What are the inputs/outputs?"
  - "Which file contains X symbol?"

### L2 (Pseudocode)
- **Best for:** Algorithm understanding, logic flow
- **Token cost:** ~150 tokens (85% savings vs L4)
- **Quality:** >90% similarity for reasoning tasks
- **Use cases:**
  - "How does this algorithm work?"
  - "What's the execution flow?"
  - "Explain the logic step-by-step"

### L4 (Full Code)
- **Best for:** Code generation, complex refactoring
- **Token cost:** ~1000 tokens (baseline)
- **Quality:** 100% (full context)
- **Use cases:**
  - "Write code to extend this function"
  - "Refactor this implementation"
  - "Generate test cases for this code"

## Quality Validation Results

A/B testing shows:
- L0/L1 for factual: 98% similarity, 97.5% token savings ✅
- L2 for reasoning: 92% similarity, 85% savings ✅
- L4 for code gen: Required for maintaining quality ❌ Can't compress

**Recommendation:** Use L4 for code generation to maintain quality.
"""

    l0l1_context = """
L0: Progressive disclosure has 3 levels: L0/L1 for factual (97.5% savings), L2 for reasoning (85% savings), L4 for code generation (no compression)
L1: @io query_type:str -> recommended_level:str
@quality L0/L1:98%, L2:92%, L4:100%
@recommendation code_generation -> use_L4_full_code
"""

    return validator.run_ab_test(
        test_case_id=2,
        query=query,
        full_context=full_context,
        l0l1_context=l0l1_context,
        query_type="reasoning",
        threshold=0.92
    )


def run_test_case_3(validator: ContextQualityValidator):
    """Test Case 3: Code Generation - Expected to fail/struggle (>0.85)"""
    print("\n=== Test Case 3: Code Generation ===")

    query = "Write Python code to implement a symbol search function using FTS5."

    full_context = """
# Symbol Search Implementation (search command)

```python
@cli.command()
@click.option("--query", required=True, help="Search query string")
@click.option("--fields", default="l0,l1", help="Fields to search (l0,l1)")
@click.option("--limit", default=10, type=int, help="Max results")
@click.option("--kind", help="Filter by symbol kind")
def search(query, fields, limit, kind):
    \"\"\"Search symbols using FTS5 full-text search.\"\"\"
    conn = ensure_db()

    # Validate fields
    search_fields = [f.strip() for f in fields.split(',')]
    indexed_fields = [f for f in search_fields if f in ['l0', 'l1']]

    if not indexed_fields:
        click.echo(json.dumps({
            "error": "no_indexed_fields",
            "hint": "FTS5 only indexes l0 and l1"
        }))
        sys.exit(2)

    # Build FTS5 query
    fts_query = f\"\"\"
        SELECT
            s.repo_path, s.name, s.kind,
            s.start_line, s.end_line,
            s.l0_overview, s.l1_contract,
            s.content_hash, fts.rank
        FROM symbols_fts fts
        JOIN symbols s ON fts.rowid = s.id
        WHERE symbols_fts MATCH ?
    \"\"\"

    params = [query]
    if kind:
        fts_query += " AND s.kind = ?"
        params.append(kind)

    fts_query += " ORDER BY fts.rank LIMIT ?"
    params.append(limit)

    # Execute query
    results = conn.execute(fts_query, params).fetchall()

    # Format output
    output = {
        "query": query,
        "fields": search_fields,
        "count": len(results),
        "results": [dict(r) for r in results]
    }

    click.echo(json.dumps(output, indent=2))
```

## Key Implementation Details

1. **FTS5 Virtual Table:** symbols_fts indexes l0_overview and l1_contract
2. **MATCH Syntax:** Simple query (not column-specific)
3. **Join Pattern:** Join fts with symbols on rowid = symbol.id
4. **Ranking:** ORDER BY fts.rank for relevance
5. **Kind Filter:** Optional WHERE clause for symbol.kind
6. **Error Handling:** Validate fields before query
"""

    l0l1_context = """
L0: Symbol search uses FTS5 virtual table to search l0/l1 fields with optional kind filtering
L1: @io query:str, fields:list, limit:int, kind:str -> results:list
@fts5 symbols_fts MATCH query JOIN symbols ON rowid=id
@ranking ORDER BY fts.rank LIMIT N
"""

    return validator.run_ab_test(
        test_case_id=3,
        query=query,
        full_context=full_context,
        l0l1_context=l0l1_context,
        query_type="code",
        threshold=0.85
    )


def run_test_case_4(validator: ContextQualityValidator):
    """Test Case 4: Decision Making - High similarity expected (>0.95)"""
    print("\n=== Test Case 4: Decision Making ===")

    query = "I need to add a new symbol to the database. Should I use 'ingest' or 'patch' command?"

    full_context = """
# File State Contract

## The Golden Rule

**BEFORE any file operation, run:** `agentdb inventory`

Then follow this decision tree:
- **If db_state=missing**: Use `agentdb ingest` with FULL file + AGTAG
- **If db_state=indexed**: Use `agentdb patch` with unified diff only

## Why This Matters

The system tracks file state to optimize storage:
- **missing**: File not in database → needs full ingest
- **indexed**: File already tracked → send incremental diff only

## Commands

### agentdb ingest
**Use when:** db_state=missing (new file)
**Input:** Full file content via stdin
**Requirements:** AGTAG block at EOF
**Output:** File hash, symbols extracted
**Error:** Rejects if file already indexed

### agentdb patch
**Use when:** db_state=indexed (existing file)
**Input:** Unified diff via stdin + AGTAG_PATCH_FINAL_FILE envelope
**Requirements:** Exact hash match (--hash-before parameter)
**Output:** Updated hash, modified symbols
**Error:** Hash mismatch = concurrent modification

## Example Workflow

```bash
# Step 1: Check state
agentdb inventory | grep "src/example.py"
# Output: {"repo_path": "src/example.py", "db_state": "indexed", "file_hash": "sha256:abc123"}

# Step 2: Decision
# State is "indexed" → use patch

# Step 3: Create patch
git diff src/example.py > patch.diff
# Add AGTAG envelope
cat patch.diff AGTAG_ENVELOPE | agentdb patch --path src/example.py --hash-before sha256:abc123
```

## Anti-Patterns

❌ DON'T: Ingest already-indexed files (rejected at core.py:122)
❌ DON'T: Patch missing files (no base to patch against)
❌ DON'T: Skip inventory check (leads to wrong command choice)
"""

    l0l1_context = """
L0: Use 'ingest' for new files (db_state=missing), use 'patch' for existing files (db_state=indexed)
L1: @decision_rule check_inventory_first
@if db_state=missing -> agentdb_ingest_full_file
@if db_state=indexed -> agentdb_patch_diff_only
@error ingest_indexed_file -> rejected_at_core.py:122
"""

    return validator.run_ab_test(
        test_case_id=4,
        query=query,
        full_context=full_context,
        l0l1_context=l0l1_context,
        query_type="decision",
        threshold=0.95
    )


def run_test_case_5(validator: ContextQualityValidator):
    """Test Case 5: Multi-Step Task - Medium similarity expected (>0.90)"""
    print("\n=== Test Case 5: Multi-Step Task ===")

    query = "Create an implementation plan for adding TypeScript auto-tagging support."

    full_context = """
# Auto-Tagger System Architecture

## Current Implementation

### 1. Markdown Auto-Tagger (core.py:1100-1200)
- Extracts: Section headings (## Header)
- L0: Heading text
- L1: Section level + word count
- L2: First paragraph preview
- Trigger: `--auto-tag` flag on .md files

### 2. Python Auto-Tagger (core.py:200-400)
- Extracts: Functions, classes via AST
- L0: Docstring first line
- L1: Function signature + return type
- L2: Full docstring
- L4: Full source code
- Always active for .py files

## Extension Pattern

To add TypeScript auto-tagger:

### Step 1: Create TypeScript Parser (1-2 hours)
File: `src/agentdb/auto_taggers/typescript_tagger.py`

```python
import re
from typing import List, Dict

def extract_typescript_symbols(content: str) -> List[Dict]:
    \"\"\"Parse TypeScript and extract functions/interfaces/types.\"\"\"
    symbols = []

    # Extract functions: function name(...): Type
    for match in re.finditer(r'function\\s+(\\w+)\\([^)]*\\):\\s*(\\w+)', content):
        symbols.append({
            'name': match.group(1),
            'kind': 'function',
            'return_type': match.group(2),
            'l0_overview': f"TypeScript function {match.group(1)}",
            'l1_contract': f"@io ... -> {match.group(2)}"
        })

    # Extract interfaces
    # Extract types
    # Extract classes

    return symbols
```

### Step 2: Integrate with core.py (30 min)
Update `ingest` command:

```python
if auto_tag:
    if safe_path.endswith('.ts') or safe_path.endswith('.tsx'):
        from agentdb.auto_taggers.typescript_tagger import generate_typescript_agtag
        content = generate_typescript_agtag(content, safe_path)
```

### Step 3: Add Tests (1 hour)
File: `tests/test_typescript_auto_tag.py`

```python
def test_typescript_function_extraction():
    code = "function hello(name: string): string { return `Hi ${name}`; }"
    agtag = extract_typescript_symbols(code)
    assert agtag[0]['name'] == 'hello'
    assert agtag[0]['kind'] == 'function'
```

### Step 4: Documentation (30 min)
Update README with TypeScript support examples

## Timeline

- **Total:** ~4 hours
- **Priority:** Medium (Python + Markdown cover 80% use cases)
- **Dependencies:** None
- **Risk:** Regex parsing fragile, consider using TypeScript compiler API
"""

    l0l1_context = """
L0: Add TypeScript auto-tagger in 4 steps: create parser (2h), integrate with core.py (30min), add tests (1h), docs (30min) = 4h total
L1: @steps 1:create_typescript_parser, 2:integrate_core_py, 3:add_tests, 4:update_docs
@timeline total:4h, priority:medium
@dependencies none, @risk regex_parsing_fragile
"""

    return validator.run_ab_test(
        test_case_id=5,
        query=query,
        full_context=full_context,
        l0l1_context=l0l1_context,
        query_type="multi_step",
        threshold=0.90
    )


def run_test_case_6(validator: ContextQualityValidator):
    """Test Case 6: Edge Case Handling"""
    print("\n=== Test Case 6: Edge Case Handling ===")

    query = "What happens if I try to ingest a file that's already indexed?"

    full_context = """
# Error Handling: indexed_file_rejects_full_content

## Implementation (core.py:122-128)

```python
@cli.command()
def ingest(path, auto_tag):
    conn = ensure_db()
    # ... path validation ...

    # Check DB state
    row = conn.execute("SELECT db_state FROM files WHERE repo_path=?", (safe_path,)).fetchone()
    state = row["db_state"] if row else "missing"

    if state != "missing":
        click.echo(json.dumps({
            "error": "indexed_file_rejects_full_content",
            "path": safe_path,
            "hint": "Use agentdb patch instead"
        }))
        sys.exit(2)  # Error exit code

    # ... continue with ingest ...
```

## Why This Happens

1. **File State Contract:** Files must be either 'missing' or 'indexed'
2. **Optimization:** Indexed files use incremental patching to save space
3. **Protocol Violation:** Sending full content for indexed file breaks contract

## Error Response

```json
{
  "error": "indexed_file_rejects_full_content",
  "path": "src/example.py",
  "hint": "Use agentdb patch instead"
}
```

**Exit Code:** 2 (error)

## Solution

Use the correct command based on state:

```bash
# Check state first
agentdb inventory | jq '.[] | select(.repo_path=="src/example.py")'

# If db_state="indexed":
agentdb patch --path src/example.py --hash-before SHA < patch.diff

# If db_state="missing":
agentdb ingest --path src/example.py < src/example.py
```

## Related Errors

- `hash_conflict`: Patch hash doesn't match current file
- `agtag_missing`: File lacks required AGTAG block
- `unsafe_path`: Path attempts directory traversal
"""

    l0l1_context = """
L0: Ingesting an already-indexed file is rejected with error "indexed_file_rejects_full_content" (exit code 2), use patch instead
L1: @error indexed_file_rejects_full_content
@location core.py:122
@exit_code 2
@solution use_agentdb_patch_for_indexed_files
"""

    return validator.run_ab_test(
        test_case_id=6,
        query=query,
        full_context=full_context,
        l0l1_context=l0l1_context,
        query_type="factual",
        threshold=0.95
    )


def run_test_case_7(validator: ContextQualityValidator):
    """Test Case 7: Ambiguous Query"""
    print("\n=== Test Case 7: Ambiguous Query ===")

    query = "How do I update a symbol?"

    full_context = """
# Updating Symbols: Two Scenarios

## Scenario 1: Symbol Code Changed (Use Patch)

When the **implementation** of a symbol changes but structure stays same:

```bash
# Example: Function body changed
# Before:
def calculate(x): return x * 2

# After:
def calculate(x): return x * 3

# Solution: Use patch
git diff src/calc.py > changes.diff
agentdb patch --path src/calc.py --hash-before <HASH> < changes.diff
```

**When:** Implementation details changed, L0-L4 need updating
**Command:** `agentdb patch`
**Input:** Unified diff + AGTAG_PATCH_FINAL_FILE envelope

## Scenario 2: Symbol Metadata Only (Manual DB Update)

When only L0/L1 annotations change (rare edge case):

```bash
# Only the L0 description improved
# Implementation unchanged

# Solution: Direct DB update (advanced users only)
sqlite3 .agentdb/agent.sqlite "UPDATE symbols SET l0_overview='New description' WHERE name='calculate'"
```

**When:** Metadata-only changes (unusual)
**Command:** Direct SQL
**Caution:** Bypass normal workflow, only for experts

## Scenario 3: Symbol Renamed/Moved

When symbol name or file location changes:

```bash
# Symbol renamed: calculate → compute

# Solution 1: Delete old, ingest new
agentdb inventory  # Note hash
# Delete old record (manual SQL)
# Ingest file with new symbol name

# Solution 2: Patch with rename in diff
git mv old.py new.py
git diff --cached > changes.diff
agentdb patch ...
```

**When:** Structural changes
**Command:** Depends on scenario
**Complexity:** High, may need manual cleanup

## Recommendation

**95% of updates:** Use `agentdb patch` (Scenario 1)
**5% edge cases:** Check with expert or docs
"""

    l0l1_context = """
L0: Update symbols using 'agentdb patch' for code changes (95% cases), or direct SQL for metadata-only updates (5%, advanced)
L1: @scenario code_changed -> use_patch_command
@scenario metadata_only -> direct_sql_advanced
@scenario renamed_moved -> complex_consult_docs
@recommendation use_patch_for_95_percent_of_cases
"""

    return validator.run_ab_test(
        test_case_id=7,
        query=query,
        full_context=full_context,
        l0l1_context=l0l1_context,
        query_type="decision",
        threshold=0.92
    )


def run_test_case_8(validator: ContextQualityValidator):
    """Test Case 8: Cross-Domain Question"""
    print("\n=== Test Case 8: Cross-Domain Question ===")

    query = "How does the FTS5 search interact with the progressive disclosure system?"

    full_context = """
# FTS5 + Progressive Disclosure Integration

## Architecture Overview

FTS5 search operates at **L0/L1 level only**, optimizing for speed and relevance:

```
User Query
    ↓
[FTS5 Search] → Searches l0_overview + l1_contract
    ↓
[Result Ranking] → ORDER BY fts.rank
    ↓
[Symbol IDs] → Matched symbol rowids
    ↓
[Progressive Disclosure] → User can zoom to L2/L3/L4 on demand
```

## Why FTS5 Only Indexes L0/L1

1. **Token Efficiency:** L0+L1 = ~25 tokens vs L4 = ~1000 tokens
2. **Search Quality:** 98% of searches satisfied by overview+contract
3. **Performance:** Smaller index = faster queries
4. **Relevance:** L0/L1 contains "what" and "how", sufficient for matching

## Workflow Example

```bash
# Step 1: User searches for "token validation"
agentdb search --query "token validation"

# FTS5 searches:
# - l0_overview: "Validates JWT tokens..."
# - l1_contract: "@io token:str -> dict | None"
# Returns: symbol IDs ranked by relevance

# Step 2: User wants details on top result
agentdb focus --handle "ctx://src/auth.py::validate_token@sha256:ANY" --depth 1

# Returns:
# - L0: "Validates JWT tokens..." (cached from FTS5)
# - L1: "@io token:str -> dict | None" (cached from FTS5)
# - Neighbor symbols (depth=1)

# Step 3: User needs implementation details
agentdb zoom --handle "ctx://src/auth.py::validate_token@sha256:ANY" --level 4

# Returns:
# - L4: Full source code (fetched on demand)
```

## Performance Benefits

| Operation | Without Progressive | With Progressive | Savings |
|-----------|---------------------|------------------|---------|
| Search | 1000 tokens/result | 25 tokens/result | 97.5% |
| Browse | 10 results × 1000 | 10 × 25 | 97.5% |
| Zoom | N/A | +975 tokens once | On demand |

**Key Insight:** FTS5 provides "entry point" at L0/L1, user chooses depth.
"""

    l0l1_context = """
L0: FTS5 searches only L0/L1 (25 tokens/result vs 1000), providing ranked entry points, then users zoom to L2/L3/L4 on demand for details
L1: @flow FTS5_search_L0L1 -> ranked_results -> user_zoom_L2_L3_L4_on_demand
@savings 97.5% (25 vs 1000 tokens)
@quality 98% searches satisfied by L0/L1
"""

    return validator.run_ab_test(
        test_case_id=8,
        query=query,
        full_context=full_context,
        l0l1_context=l0l1_context,
        query_type="reasoning",
        threshold=0.90
    )


def run_test_case_9(validator: ContextQualityValidator):
    """Test Case 9: Historical Context"""
    print("\n=== Test Case 9: Historical Context ===")

    query = "What problem led to the creation of the AGTAG system?"

    full_context = """
# AGTAG System Origin Story

## The Problem (Pre-AGTAG Era)

Before AGTAG, agents faced the "context explosion" problem:

### Scenario: Agent Needs to Understand a 500-Line Python File

**Without AGTAG:**
```
User: "What does calculate_metrics do?"

Agent options:
1. Read full file (500 lines) → 12,500 tokens
2. Use AST (complex, fragile) → Still needs full parse
3. Guess based on name → Inaccurate

Result: 💸 $0.038 per query, slow, wastes context window
```

**The Core Issues:**
1. **No metadata layer:** Had to parse code every time
2. **All-or-nothing:** Either full file or nothing
3. **No persistence:** Re-parse on every query
4. **Token waste:** 95% of file irrelevant to query

## The Solution: AGTAG v1

### Design Philosophy

**"Git for symbol-level context"** - version control for metadata

1. **Persistent Metadata:** Store L0-L4 once, query forever
2. **Progressive Disclosure:** Start cheap (L0), zoom deeper if needed
3. **File-Embedded:** AGTAG lives in file (portable, version-controlled)
4. **Format-Agnostic:** HTML comments work in any language

### AGTAG Structure

```
[Your code]

```

### Impact

**Same query now:**
```
User: "What does calculate_metrics do?"

Agent: Reads L0 only (10 tokens)
→ "Computes usage metrics from logs"

Cost: $0.00003 vs $0.038 = 99.9% savings
```

## Key Innovations

1. **Incremental Patching:** Update diffs, not full files
2. **FTS5 Integration:** Fast search on L0/L1
3. **Auto-Tagging:** Generate AGTAG from code automatically
4. **Quality Validation:** A/B tests prove 98% semantic similarity

## Timeline

- **2024-12**: Problem identified (context explosion)
- **2025-01**: AGTAG v1 spec created
- **2025-01**: AgentDB MVP implemented
- **2025-10**: Quality validation (this mission!)
"""

    l0l1_context = """
L0: AGTAG was created to solve "context explosion" where agents wasted 12,500 tokens reading 500-line files for simple queries, now uses L0 (10 tokens) = 99.9% savings
L1: @problem context_explosion:12500_tokens_per_query
@solution AGTAG_v1:progressive_disclosure_L0_L1_L2_L4
@savings 99.9% (10 vs 12500 tokens)
@timeline 2024-12_problem -> 2025-01_solution -> 2025-10_validation
"""

    return validator.run_ab_test(
        test_case_id=9,
        query=query,
        full_context=full_context,
        l0l1_context=l0l1_context,
        query_type="factual",
        threshold=0.95
    )


def run_test_case_10(validator: ContextQualityValidator):
    """Test Case 10: Future Planning"""
    print("\n=== Test Case 10: Future Planning ===")

    query = "What are the next planned features after quality validation?"

    full_context = """
# AgentDB Roadmap (Post-Quality Validation)

## Phase 1: Core Stability (Week 1-2)
- ✅ CR-8 Phase 3: LRU caching (COMPLETE)
- ✅ Task 4: Search command (COMPLETE)
- 🔄 Task 5: Quality validation (IN PROGRESS)

## Phase 2: Production Readiness (Week 3-4)

### Priority 1: Dashboard Integration
**Goal:** Supabase dashboard consumes AgentDB data

**Tasks:**
1. Create FastAPI endpoints wrapping CLI commands
2. Add authentication/rate limiting
3. Deploy to production Supabase instance
4. Monitor performance metrics

**Estimated Time:** 8-10 hours
**Blocker:** None
**Owner:** Backend team

### Priority 2: Multi-Language Auto-Taggers
**Goal:** Extend beyond Python/Markdown

**Languages:**
- TypeScript/JavaScript (4h)
- Go (3h)
- Rust (4h)
- SQL (2h)
- Generic text (2h)

**Estimated Time:** 15 hours total
**Blocker:** Quality validation must pass first
**Owner:** Backend team

### Priority 3: Distributed AgentDB
**Goal:** Multi-repo coordination

**Features:**
- Cross-repo symbol search
- Dependency graph across repos
- Shared knowledge base
- Team collaboration features

**Estimated Time:** 20-30 hours
**Blocker:** Core stability
**Owner:** TBD

## Phase 3: Advanced Features (Week 5+)

### A: Semantic Symbol Search
- Embedding-based search (not just FTS5)
- "Find similar functions"
- Concept-based queries

### B: Agent Coordination Protocol
- Multiple agents share AgentDB
- Conflict resolution
- Incremental learning

### C: VS Code Extension
- IDE integration
- Inline symbol tooltips
- Jump-to-definition via ctx:// handles

## Success Metrics

- [ ] Quality validation passes (≥80% test cases >0.90 similarity)
- [ ] Dashboard integration complete
- [ ] 5+ language auto-taggers deployed
- [ ] Production deployment successful

## Timeline

**Aggressive:** 4 weeks to production
**Realistic:** 6 weeks with buffer
**Blocker:** Quality validation results
"""

    l0l1_context = """
L0: After quality validation, next features are: Dashboard integration (8-10h), multi-language auto-taggers (15h), distributed AgentDB (20-30h), then advanced features like semantic search
L1: @phase1 core_stability:complete
@phase2 dashboard_integration:8-10h, multi_language_taggers:15h, distributed_agentdb:20-30h
@phase3 semantic_search, agent_coordination, vscode_extension
@timeline aggressive:4weeks, realistic:6weeks
@blocker quality_validation_must_pass_first
"""

    return validator.run_ab_test(
        test_case_id=10,
        query=query,
        full_context=full_context,
        l0l1_context=l0l1_context,
        query_type="factual",
        threshold=0.95
    )


def main():
    """Run all 10 quality validation test cases."""
    import argparse

    parser = argparse.ArgumentParser(description="Run quality validation test cases")
    parser.add_argument("--test-case", type=int, help="Run specific test case (1-10)")
    parser.add_argument("--model", default="claude-3-5-haiku-20241022", help="Anthropic model")
    args = parser.parse_args()

    print("=" * 70)
    print("AgentDB Quality Validation: Full Context vs L0/L1 Compression")
    print("=" * 70)

    # Initialize validator
    validator = ContextQualityValidator(model=args.model)

    # Run test cases
    test_cases = {
        1: run_test_case_1,
        2: run_test_case_2,
        3: run_test_case_3,
        4: run_test_case_4,
        5: run_test_case_5,
        6: run_test_case_6,
        7: run_test_case_7,
        8: run_test_case_8,
        9: run_test_case_9,
        10: run_test_case_10,
    }

    if args.test_case:
        if args.test_case not in test_cases:
            print(f"Error: Test case {args.test_case} not found (valid: 1-10)")
            sys.exit(1)

        result = test_cases[args.test_case](validator)
        print(f"\n{'='*70}")
        print(f"Test Case {result.test_case_id}: {result.verdict}")
        print(f"Similarity: {result.similarity_score:.3f} (threshold: {result.threshold})")
        print(f"Token savings: {result.token_savings_pct:.1f}%")
        print(f"{'='*70}")
    else:
        print("\nRunning all 10 test cases...\n")
        for test_id in sorted(test_cases.keys()):
            result = test_cases[test_id](validator)
            print(f"\n✓ Test Case {result.test_case_id}: {result.verdict} (similarity: {result.similarity_score:.3f})")

        # Generate report
        print("\n" + "="*70)
        print("Generating quality validation report...")
        print("="*70 + "\n")

        metrics = validator.generate_report()

        print("\n" + "="*70)
        print(f"FINAL VERDICT: {metrics['overall_verdict']}")
        print(f"Pass Rate: {metrics['pass_rate']*100:.1f}%")
        print(f"Avg Similarity: {metrics['avg_similarity']:.3f}")
        print(f"Avg Token Savings: {metrics['avg_token_savings']*100:.1f}%")
        print("="*70)


if __name__ == "__main__":
    main()

AGTAG_METADATA = """

<!--AGTAG v1 START-->
{
  "version": "v1",
  "symbols": [
    {
      "name": "run_test_case_1",
      "kind": "function",
      "qualified_name": "tests.quality_validation.run_quality_validation.run_test_case_1",
      "lines": [
        22,
        72
      ],
      "summary_l0": "Helper function run_test_case_1 supporting test utilities.",
      "contract_l1": "def run_test_case_1(validator: ContextQualityValidator)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/quality_validation/run_quality_validation.py"
    },
    {
      "name": "run_test_case_2",
      "kind": "function",
      "qualified_name": "tests.quality_validation.run_quality_validation.run_test_case_2",
      "lines": [
        75,
        137
      ],
      "summary_l0": "Helper function run_test_case_2 supporting test utilities.",
      "contract_l1": "def run_test_case_2(validator: ContextQualityValidator)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/quality_validation/run_quality_validation.py"
    },
    {
      "name": "run_test_case_3",
      "kind": "function",
      "qualified_name": "tests.quality_validation.run_quality_validation.run_test_case_3",
      "lines": [
        140,
        228
      ],
      "summary_l0": "Helper function run_test_case_3 supporting test utilities.",
      "contract_l1": "def run_test_case_3(validator: ContextQualityValidator)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/quality_validation/run_quality_validation.py"
    },
    {
      "name": "run_test_case_4",
      "kind": "function",
      "qualified_name": "tests.quality_validation.run_quality_validation.run_test_case_4",
      "lines": [
        231,
        308
      ],
      "summary_l0": "Helper function run_test_case_4 supporting test utilities.",
      "contract_l1": "def run_test_case_4(validator: ContextQualityValidator)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/quality_validation/run_quality_validation.py"
    },
    {
      "name": "run_test_case_5",
      "kind": "function",
      "qualified_name": "tests.quality_validation.run_quality_validation.run_test_case_5",
      "lines": [
        311,
        415
      ],
      "summary_l0": "Helper function run_test_case_5 supporting test utilities.",
      "contract_l1": "def run_test_case_5(validator: ContextQualityValidator)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/quality_validation/run_quality_validation.py"
    },
    {
      "name": "run_test_case_6",
      "kind": "function",
      "qualified_name": "tests.quality_validation.run_quality_validation.run_test_case_6",
      "lines": [
        418,
        505
      ],
      "summary_l0": "Helper function run_test_case_6 supporting test utilities.",
      "contract_l1": "def run_test_case_6(validator: ContextQualityValidator)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/quality_validation/run_quality_validation.py"
    },
    {
      "name": "run_test_case_7",
      "kind": "function",
      "qualified_name": "tests.quality_validation.run_quality_validation.run_test_case_7",
      "lines": [
        508,
        597
      ],
      "summary_l0": "Helper function run_test_case_7 supporting test utilities.",
      "contract_l1": "def run_test_case_7(validator: ContextQualityValidator)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/quality_validation/run_quality_validation.py"
    },
    {
      "name": "run_test_case_8",
      "kind": "function",
      "qualified_name": "tests.quality_validation.run_quality_validation.run_test_case_8",
      "lines": [
        600,
        683
      ],
      "summary_l0": "Helper function run_test_case_8 supporting test utilities.",
      "contract_l1": "def run_test_case_8(validator: ContextQualityValidator)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/quality_validation/run_quality_validation.py"
    },
    {
      "name": "run_test_case_9",
      "kind": "function",
      "qualified_name": "tests.quality_validation.run_quality_validation.run_test_case_9",
      "lines": [
        686,
        779
      ],
      "summary_l0": "Helper function run_test_case_9 supporting test utilities.",
      "contract_l1": "def run_test_case_9(validator: ContextQualityValidator)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/quality_validation/run_quality_validation.py"
    },
    {
      "name": "run_test_case_10",
      "kind": "function",
      "qualified_name": "tests.quality_validation.run_quality_validation.run_test_case_10",
      "lines": [
        782,
        885
      ],
      "summary_l0": "Helper function run_test_case_10 supporting test utilities.",
      "contract_l1": "def run_test_case_10(validator: ContextQualityValidator)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/quality_validation/run_quality_validation.py"
    },
    {
      "name": "main",
      "kind": "function",
      "qualified_name": "tests.quality_validation.run_quality_validation.main",
      "lines": [
        888,
        947
      ],
      "summary_l0": "Helper function main supporting test utilities.",
      "contract_l1": "def main()",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/quality_validation/run_quality_validation.py"
    }
  ]
}
<!--AGTAG v1 END-->
"""
