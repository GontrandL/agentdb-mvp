# CLAUDE.md

**⚠️ CONTRACT ANCHOR: All agents working in this repository MUST follow these rules.**

This file serves as the system prompt seed for Claude Code (claude.ai/code) and any other AI agent working with this codebase. The rules defined here are **invariant constraints** that never change across sessions or tasks.

---

## 🚀 Quick Reference (Agent Onboarding)

**New agents: Read this first, then read "INVARIANT CONSTRAINTS" section.**

### The Core Concept
This is a **symbol metadata database** for AI agents. Think of it as "Git for symbol-level context" with progressive disclosure (L0-L4 zoom levels).

### The Golden Rule
```
MISSING file → ingest FULL content + AGTAG
INDEXED file → patch DIFF only + envelope
ALWAYS check inventory FIRST
```

### Most Common Commands
```bash
agentdb init                    # Initialize DB (once per project)
agentdb inventory               # Check file states (run BEFORE any operation)
agentdb ingest --path X < file  # Add new file (db_state=missing only)
agentdb patch --path X --hash-before Y < diff  # Update indexed file
agentdb focus --handle "ctx://X::Y@sha256:ANY" --depth 1  # Get context
```

### Critical File References
- **Schema**: schema.sql (database tables)
- **AGTAG spec**: src/agentdb/agtag.py:4-31 (TypedDict definitions)
- **CLI logic**: src/agentdb/core.py (all commands implemented here)
- **Invariant rules**: Lines 86-184 below (READ CAREFULLY)

### Token Optimization Strategy (VALIDATED ✅)

**Status:** ✅ Production-ready based on comprehensive validation (L0-L4 depth testing + Quality A/B testing)

**Smart Escalation Strategy:**
Start cheap, escalate only when needed using query-type detection:

#### Default Tier Distribution (70/20/10)
- **70% queries: L0/L1** (~30 tokens) - Factual, decisions, status checks
- **20% queries: L2** (~60 tokens) - Reasoning, planning, workflows
- **10% queries: L4** (~200 tokens) - Code generation, editing

**Average token usage: ~53 tokens vs 200 tokens (L4 always) = 73.5% savings** 🚀

#### Query Type Detection

**Use L0/L1 (focus --depth 1) for:**
- ✅ Factual queries: "what is", "how do I", "should I", "which"
- ✅ Status checks: "current status", "check if", "list"
- ✅ Simple decisions: "use X or Y?", "when to"
- **Quality: 97.5% similarity validated**
- **Savings: 65-80% tokens**

**Escalate to L2 (zoom --level 2) for:**
- ⚠️ Complex reasoning: "explain why", "how does it work"
- ⚠️ Multi-step planning: "create plan for", "steps to", "design"
- ⚠️ Workflows: "what's the process", "how do I implement"
- **Quality: 90.5% similarity validated**
- **Savings: 40-60% tokens**

**Escalate to L4 (zoom --level 4) for:**
- ❌ Code generation: "write code", "implement", "generate function"
- ❌ Code editing: "modify", "refactor", "fix bug in"
- ❌ Implementation details: "show me the code", "exact syntax"
- **Quality: 100% (full source)**
- **Savings: 0% but necessary**

#### Validated Real-World Performance
- Session startup: 94.8% token savings (1,447 words → 75 words)
- 10/10 depth tests passed
- 92.8% average semantic similarity
- <200ms query response time

**Reference:** See [VALIDATION_INTEGRATION_ANALYSIS.md](VALIDATION_INTEGRATION_ANALYSIS.md) for complete validation results

### Cost Optimization: Background Router Delegation
For tasks suitable for background processing, use **claude-code-router** to delegate to cost-effective models:
- **Anthropic Claude 3.5 Sonnet:** $3/M tokens (premium, interactive tasks)
- **Z.AI GLM-4.5-air:** $0.14/M tokens (background tasks, **95% cost savings**)

**Router Status:** ✅ Running at http://127.0.0.1:3456 (PID file: `~/.claude-code-router/.claude-code-router.pid`)

---

## Project Overview

**agentdb-mvp** is a per-project database system designed for coding agents. It stores symbol metadata in `./.agentdb/` using SQLite with FTS5 full-text search. The system uses a layered content representation (L0-L4) and enforces a strict contract: full files only when `db_state=missing`, otherwise unified diffs.

## Core Architecture

### Database Schema (schema.sql)
- **files table**: Tracks file hashes and db_state ('missing' or 'indexed')
- **symbols table**: Stores symbol metadata with 5 levels of detail (L0-L4)
- **edges table**: Tracks symbol relationships (dependencies, calls, etc.)
- **symbols_fts**: FTS5 virtual table for fast symbol search
- **ops_log**: Audit trail of all operations

### Symbol Levels (L0-L4)
The system uses progressive detail levels:
- **L0**: One-line overview/summary
- **L1**: Contract (input/output, invariants)
- **L2**: Pseudocode/algorithm description
- **L3**: AST excerpt (JSON)
- **L4**: Full source code

### AGTAG v1 Format

**CRITICAL:** AGTAG format varies by file type. Using incorrect format will break syntax!

#### For Python Files (.py) - MUST Use Variable Wrapper

```python
# Your code here
def example(a, b):
    return a + b

# AGTAG block MUST be in a variable (valid Python syntax)
AGTAG_METADATA = """<!--AGTAG v1 START-->
{"version":"v1","symbols":[{"path":"src/example.py","name":"example","kind":"function","lines":[1,2],"summary_l0":"adds two numbers","contract_l1":"@io a:int,b:int -> int"}]}
<!--AGTAG v1 END-->
"""
```

**Why:** HTML comments `<!--` are NOT valid Python syntax. Wrapping in `AGTAG_METADATA = """..."""` makes it a valid string literal.

**WRONG (breaks imports!):**
```python
def example(a, b):
    return a + b

<!--AGTAG v1 START-->  # ← SyntaxError!
{"version":"v1",...}
<!--AGTAG v1 END-->
```

#### For HTML/Markdown Files (.html, .md) - Direct Comments

```html
<!-- Your content here -->

<!--AGTAG v1 START-->
{"version":"v1","symbols":[...],"docs":[...],"tests":[...]}
<!--AGTAG v1 END-->
```

**Why:** HTML comments are native syntax in HTML/Markdown files.

#### Validation Rules

Before ingesting ANY file with AGTAG:
- ✅ Python files: MUST have `AGTAG_METADATA = """..."""` wrapper
- ✅ HTML/Markdown: Can use direct `<!--AGTAG v1 START-->`
- ✅ Test that file still imports/parses after adding AGTAG
- ❌ NEVER add raw HTML comments to Python files

Schema defined in `src/agentdb/agtag.py:4-31`
See `examples/example.py` for correct Python format.

## Development Commands

### Environment Setup
```bash
# Create venv (Python 3.10+)
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode
pip install -e .

# Install dev dependencies (if needed)
pip install pytest
```

### Core CLI Commands
```bash
# Initialize database (creates .agentdb/agent.sqlite)
agentdb init

# List all tracked files and their states
agentdb inventory

# Ingest new file (only when db_state=missing)
agentdb ingest --path src/example.py < examples/example.py

# Query context (L0/L1 + neighbors)
agentdb focus --handle "ctx://src/example.py::example@sha256:ANY" --depth 1

# Zoom to specific detail level
agentdb zoom --handle "ctx://src/example.py::example@sha256:ANY" --level 2

# Apply patch to indexed file (requires matching hash)
agentdb patch --path src/example.py --hash-before <HASH> < patch.diff
```

### Running Tests
```bash
# Run all tests
python3 -m pytest

# Run specific test
python3 -m pytest tests/test_ingest_and_focus.py -v

# Run with quiet output
python3 -m pytest -q
```

## 💰 COST OPTIMIZATION: BACKGROUND ROUTER DELEGATION

### Rule: Delegate Background Tasks to Save 95% Costs

**CRITICAL:** For long-running, non-interactive tasks, ALWAYS delegate to Z.AI via claude-code-router instead of processing directly with Anthropic Claude.

### Router Configuration

**Location:** `~/.config/claude-code-router/config.json`

```json
{
  "providers": {
    "anthropic": {
      "models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"]
    },
    "z-ai": {
      "apiKey": "ee18b161f3ce4bf6a314e914429bd91b.SHTDun4RNpiQjBNl",
      "baseUrl": "https://api.z.ai/api/coding/paas/v4/",
      "models": ["glm-4.5-air", "glm-4.6", "glm-4.5"]
    }
  },
  "router": {
    "default": "anthropic,claude-3-5-sonnet-20241022",
    "background": "z-ai,glm-4.5-air",
    "think": "anthropic,claude-3-opus-20240229",
    "longContext": "anthropic,claude-3-opus-20240229"
  }
}
```

### Cost Comparison

| Model | Cost per 1M tokens | Use Case |
|-------|-------------------|----------|
| Claude 3.5 Sonnet | $3.00 | Interactive, complex reasoning |
| Claude 3 Opus | $15.00 | Long context, deep analysis |
| Z.AI GLM-4.5-air | $0.14 | Background tasks, **95% savings** |
| Z.AI GLM-4.6 | $0.20 | Latest model, still 93% savings |

### When to Delegate

**✅ DELEGATE to Z.AI (via ccr code) for:**
- Documentation generation (> 500 words)
- Test suite creation (> 10 tests)
- Code scaffolding and boilerplate
- Batch file processing
- Data transformation scripts
- Configuration file generation
- Long-form content generation
- Research and information gathering (non-interactive)
- Repetitive code patterns

**❌ KEEP on Claude Sonnet for:**
- Interactive debugging
- Complex architectural decisions
- Real-time code review
- Context-sensitive edits (< 200 lines)
- Quick file operations (< 5 files)
- Immediate clarification questions
- Security-critical decisions

### Delegation Syntax

**Basic Command:**
```bash
ccr code "Your task description here"
```

**Examples:**

```bash
# Example 1: Generate comprehensive documentation
ccr code "Create detailed API documentation for all functions in src/agentdb/core.py with examples and usage patterns"

# Example 2: Create test suite
ccr code "Generate a comprehensive pytest test suite for the intelligence_integrator module with fixtures, mocks, and edge cases"

# Example 3: Code scaffolding
ccr code "Create a new module called 'batch_processor.py' with BatchProcessor class that handles file processing with progress tracking, error handling, and retry logic"

# Example 4: Batch processing
ccr code "Write a script to migrate all Python files in src/ to add type hints based on existing usage patterns"

# Example 5: Configuration generation
ccr code "Generate a complete docker-compose.yml for the project with services for PostgreSQL, Redis, and the main app with proper networking and volumes"
```

### Router Status Check

```bash
# Check if router is running
ccr status

# View router logs
tail -f ~/.claude-code-router/logs/*.log

# Restart router if needed
ccr restart
```

**Expected Output:**
```
📊 Claude Code Router Status
════════════════════════════════════════
✅ Status: Running
🆔 Process ID: 56751
🌐 Port: 3456
📡 API Endpoint: http://127.0.0.1:3456
```

### Decision Matrix for Delegation

Use this matrix to decide whether to delegate:

| Factor | Delegate to Z.AI | Keep on Claude |
|--------|------------------|----------------|
| **Token count** | > 5,000 tokens | < 5,000 tokens |
| **Time required** | > 5 minutes | < 5 minutes |
| **Interaction needed** | None | Frequent |
| **Complexity** | Low-medium | High |
| **Output type** | Code/docs | Decisions |
| **Cost impact** | High (save $2.86/M) | Low |

### Workflow Integration

**Recommended Pattern:**

1. **Start task** → Assess if delegatable using decision matrix
2. **If delegatable** → Use `ccr code "task"`
3. **Monitor progress** → Check router logs if needed
4. **Review output** → Validate quality with Claude
5. **Integrate** → Use Claude for final integration/review

**Example Workflow:**

```bash
# Step 1: User requests comprehensive test suite
# Decision: Delegatable (>10 tests, >5000 tokens, low interaction)

# Step 2: Delegate to Z.AI
ccr code "Create comprehensive pytest test suite for dashboard/app/context/intelligence_integrator.py with 15+ test cases covering all methods, edge cases, and error conditions. Include fixtures for database mocking and sample data."

# Step 3: Claude reviews output and integrates
# (Claude validates: proper imports, correct assertions, comprehensive coverage)

# Result: 95% cost savings, same quality output
```

### Monitoring and Validation

**Check delegation success:**

```bash
# View recent router activity
tail -50 ~/.claude-code-router/logs/ccr-*.log | grep -A 5 "z-ai"

# Expected: Routing to Z.AI for background tasks
# Look for: "provider: z-ai" and "model: glm-4.5-air"
```

**Validate cost savings:**

Router automatically routes `background` type tasks to Z.AI. Verify by checking:
1. Task completion time
2. Model used (should be glm-4.5-air)
3. Token count
4. Cost calculation (tokens × $0.14/M vs tokens × $3.00/M)

### Known Issues and Limitations

**ImageAgent Errors (Non-Critical):**
Router logs may show `ImageAgent.shouldHandle` errors. These are **harmless** and don't affect text-based delegation:

```
TypeError: Cannot read properties of undefined (reading 'image')
```

**Impact:** None on text generation and code tasks.

**Z.AI Model Availability:**
- ✅ Available: `glm-4.5-air`, `glm-4.6`, `glm-4.5`
- ❌ Unavailable: `glm-4-air`, `glm-4-flash` (old model names)

### Best Practices

1. **Always use delegation for long tasks** - If you estimate >5 min processing time, delegate
2. **Batch similar tasks** - Combine multiple small tasks into one delegation
3. **Validate output quality** - Claude should review Z.AI output before integration
4. **Monitor router health** - Check `ccr status` if delegation seems slow
5. **Use clear task descriptions** - Detailed prompts improve Z.AI output quality

### Cost Impact Example

**Before Delegation (Claude Sonnet only):**
- Generate 20-test suite: ~15,000 tokens
- Cost: 15,000 × $3/M = $0.045
- Time: ~3 minutes

**After Delegation (via Router to Z.AI):**
- Same 20-test suite: ~15,000 tokens
- Cost: 15,000 × $0.14/M = $0.0021
- Time: ~3 minutes
- **Savings: $0.0429 (95%)**

**At scale (100 tasks/month):**
- Savings: $4.29/month per agent
- Team of 5 agents: **$21.45/month savings**

## 🚨 INVARIANT CONSTRAINTS (NEVER VIOLATE)

These rules are **non-negotiable** and enforced by the system. Violating them will cause command failures.

### Rule 1: File State Contract (CRITICAL)
**Before ANY file operation:**
```bash
# ALWAYS run this first
agentdb inventory
```

**Then follow this decision tree:**
- **If `db_state=missing`**: ✅ Use `agentdb ingest` with FULL file content + AGTAG
- **If `db_state=indexed`**: ✅ Use `agentdb patch` with unified diff only
- **If `db_state=indexed`**: ❌ NEVER send full file to `ingest` (will be rejected at core.py:122)

**Why this matters:** The system tracks file state to optimize storage and enforce incremental updates. Sending full content to an indexed file is a protocol violation.

### Rule 2: AGTAG Block Requirements (MANDATORY)
Every file touching symbols/tests/docs MUST have an AGTAG block:
```python
# Your code here
def example():
    pass

<!--AGTAG v1 START-->
{"version":"v1","symbols":[{"name":"example","kind":"function","lines":[1,2],"summary_l0":"...","contract_l1":"..."}]}
<!--AGTAG v1 END-->
```

**Non-negotiable requirements:**
- ✅ MUST be at end of file (EOF)
- ✅ MUST use HTML comment markers `<!--AGTAG v1 START-->` and `<!--AGTAG v1 END-->`
- ✅ MUST contain valid JSON with `"version":"v1"` and `"symbols":[]` array minimum
- ✅ Code hash is auto-calculated from content BEFORE AGTAG block (core.py:125-129)

**Enforcement:** Missing/invalid AGTAG will cause ingest failure (core.py:127-128)

### Rule 3: Handle Format (EXACT SPECIFICATION)
```
ctx://{repo_path}::{symbol_name}@{hash}#l{level}
```

**Examples:**
```bash
# Match specific version
ctx://src/agentdb/core.py::ensure_db@sha256:abc123#l1

# Match any version (common during development)
ctx://src/agentdb/core.py::ensure_db@sha256:ANY#l0

# Query all symbols in file
ctx://src/agentdb/core.py::ANY@sha256:ANY#l0
```

**Parsing:** Implemented in core.py:141-146. Invalid handles will be rejected.

### Rule 4: Patch Envelope Format (REQUIRED)
The `patch` command expects a special envelope (not standard unified diff):
```
--- a/src/example.py
+++ b/src/example.py
@@ -1,2 +1,3 @@
 def example():
-    pass
+    return 42

AGTAG_PATCH_FINAL_FILE {
  "final_file": "def example():\n    return 42\n\n<!--AGTAG v1 START-->..."
} END
```

**Why:** Naive diff application is error-prone. The `final_file` field contains the complete post-patch content, eliminating ambiguity (core.py:213-224).

**Enforcement:** Patch without `AGTAG_PATCH_FINAL_FILE` block will be rejected (core.py:217-218).

### Rule 5: Context-First Strategy (MANDATORY WORKFLOW)
**Before making ANY changes to symbols:**

```bash
# Step 1: Get overview + neighbor context (ALWAYS start here)
agentdb focus --handle "ctx://path/to/file.py::symbol@sha256:ANY" --depth 1

# Step 2: If L0/L1 insufficient, zoom to deeper levels
agentdb zoom --handle "ctx://path/to/file.py::symbol@sha256:ANY" --level 2

# Step 3: Only request L4 (full code) when absolutely necessary
agentdb zoom --handle "ctx://path/to/file.py::symbol@sha256:ANY" --level 4
```

**Rationale:**
- L0/L1 = ~50 tokens (overview + contract)
- L2 = ~200 tokens (pseudocode)
- L3 = ~500 tokens (AST excerpt)
- L4 = ~2000 tokens (full code)

Starting with L0/L1 saves **97.5% tokens** vs loading full code. Only zoom deeper when needed.

**Enforcement:** Not automated, but violating this wastes context window and is considered poor agent behavior.

## MCP Server (tools/mcp-agentdb/)

A minimal stdio MCP server skeleton is provided in `tools/mcp-agentdb/main.py`. It wraps the CLI commands and exposes them as MCP tools:
- `ingest_file`
- `focus`
- `zoom`
- `patch`

The server is a stub implementation that shells out to the CLI. Replace with a proper MCP implementation when ready.

## Module Organization

```
src/agentdb/
  core.py          - Main CLI implementation, DB operations
  agtag.py         - AGTAG v1 schema (TypedDict definitions)
  focus.py         - (placeholder for focus graph logic)
  patch.py         - (placeholder for patch application)

tools/mcp-agentdb/
  main.py          - MCP stdio server stub
  server.json      - MCP tool definitions

tests/
  test_bootstrap.py           - Basic initialization test
  test_ingest_and_focus.py    - Integration tests
```

## Hash Verification

All operations use SHA-256 hashing:
- File hashes include the full content (code + AGTAG)
- Symbol content hashes cover only the code slice (lines start_line:end_line)
- Patch command requires exact hash match to prevent conflicts (core.py:202-204)

## English-Only Inside Blocks

The system contract specifies "English only inside blocks; no prose outside blocks." This means:
- Symbol summaries, contracts, pseudocode should be in English
- Avoid adding commentary or prose outside AGTAG blocks
- Keep documentation concise and structured

## ✅ Pre-Flight Checklist (Run Before Every Operation)

Before executing ANY operation on this codebase, agents MUST verify:

### Before Creating/Ingesting Files
- [ ] Ran `agentdb inventory` to check file state
- [ ] Confirmed `db_state=missing` for target file
- [ ] File includes AGTAG block at EOF with valid JSON
- [ ] **CRITICAL:** Used correct AGTAG format for file type:
  - [ ] Python (.py): `AGTAG_METADATA = """<!--AGTAG v1 START-->..."""`
  - [ ] HTML/Markdown (.html, .md): `<!--AGTAG v1 START-->...` (direct)
- [ ] AGTAG contains minimum: `{"version":"v1","symbols":[...]}`
- [ ] All symbols have `name`, `kind`, and `summary_l0` fields
- [ ] **Validated syntax:** For Python files, tested that `import` works after AGTAG
- [ ] Using `agentdb ingest --path <path>` with stdin redirect

### Before Patching Files
- [ ] Ran `agentdb inventory` to get current file hash
- [ ] Confirmed `db_state=indexed` for target file
- [ ] Hash matches `--hash-before` parameter exactly
- [ ] Patch includes `AGTAG_PATCH_FINAL_FILE` envelope
- [ ] `final_file` contains complete post-patch content with AGTAG
- [ ] Using `agentdb patch --path <path> --hash-before <hash>` with stdin redirect

### Before Querying Context
- [ ] Starting with `focus` (L0/L1) to get overview
- [ ] Using `@sha256:ANY` to match any version during development
- [ ] Handle format is correct: `ctx://path::symbol@hash#level`
- [ ] Only escalating to `zoom` levels 2-4 if L0/L1 insufficient

### After Any Modification
- [ ] Verified changes with `agentdb focus` or `agentdb zoom`
- [ ] Confirmed new hash appears in `agentdb inventory`
- [ ] File on disk matches expected state (code + AGTAG)

## Common Patterns

### Creating a new symbol
```bash
# 1. Check current state
agentdb inventory | grep "path/to/file.py"

# 2. If missing, create file with AGTAG
cat > /tmp/newfile.py << 'EOF'
def example(a, b):
    return a + b

<!--AGTAG v1 START-->
{"version":"v1","symbols":[{"name":"example","kind":"function","lines":[1,2],"summary_l0":"adds two numbers","contract_l1":"@io a:int,b:int -> int"}]}
<!--AGTAG v1 END-->
EOF

# 3. Ingest via stdin
agentdb ingest --path path/to/file.py < /tmp/newfile.py

# 4. Verify ingestion
agentdb focus --handle "ctx://path/to/file.py::example@sha256:ANY" --depth 0
```

### Updating an existing symbol
```bash
# 1. Get current hash
HASH=$(agentdb inventory | grep "path/to/file.py" | jq -r '.file_hash')

# 2. Create patch with envelope
cat > /tmp/patch.diff << 'EOF'
--- a/path/to/file.py
+++ b/path/to/file.py
@@ -1,2 +1,3 @@
 def example(a, b):
-    return a + b
+    return a + b + 1

AGTAG_PATCH_FINAL_FILE {
  "final_file": "def example(a, b):\n    return a + b + 1\n\n<!--AGTAG v1 START-->..."
} END
EOF

# 3. Apply patch
agentdb patch --path path/to/file.py --hash-before "$HASH" < /tmp/patch.diff

# 4. Verify changes
agentdb zoom --handle "ctx://path/to/file.py::example@sha256:ANY" --level 4
```

### Querying context before edits
```bash
# 1. Start with overview (L0/L1) - cheapest, ~50 tokens
agentdb focus --handle "ctx://src/agentdb/core.py::upsert_symbols@sha256:ANY" --depth 1

# 2. If needed, get pseudocode (L2) - ~200 tokens
agentdb zoom --handle "ctx://src/agentdb/core.py::upsert_symbols@sha256:ANY" --level 2

# 3. Only if critical, get full code (L4) - ~2000 tokens
agentdb zoom --handle "ctx://src/agentdb/core.py::upsert_symbols@sha256:ANY" --level 4
```

This progressive disclosure saves **97.5% tokens** compared to always loading full code.

## 🔧 Error Recovery & Troubleshooting

### Common Errors and Solutions

#### Error: `indexed_file_rejects_full_content`
**Cause:** Tried to `ingest` a file that's already indexed (core.py:122)

**Fix:**
```bash
# Check current state
agentdb inventory | grep "path/to/file.py"

# If indexed, use patch instead
agentdb patch --path path/to/file.py --hash-before <HASH> < patch.diff
```

#### Error: `agtag_missing`
**Cause:** File doesn't have AGTAG block at EOF (core.py:127-128)

**Fix:**
```python
# Add AGTAG block at end of file
<!--AGTAG v1 START-->
{"version":"v1","symbols":[...]}
<!--AGTAG v1 END-->
```

#### Error: `hash_conflict`
**Cause:** File was modified since hash was retrieved (core.py:204)

**Fix:**
```bash
# Get fresh hash
HASH=$(agentdb inventory | grep "path/to/file.py" | jq -r '.file_hash')

# Retry patch with correct hash
agentdb patch --path path/to/file.py --hash-before "$HASH" < patch.diff
```

#### Error: `no_final_file_in_patch`
**Cause:** Patch missing `AGTAG_PATCH_FINAL_FILE` envelope (core.py:217-218)

**Fix:**
```bash
# Add envelope to patch
AGTAG_PATCH_FINAL_FILE {
  "final_file": "<complete file content>"
} END
```

#### Error: `not_found` (from zoom/focus)
**Cause:** Symbol doesn't exist in DB (core.py:179)

**Fix:**
```bash
# Verify file is ingested
agentdb inventory | grep "path/to/file.py"

# If missing, ingest first
agentdb ingest --path path/to/file.py < file.py

# If indexed, check symbol name matches exactly
agentdb focus --handle "ctx://path/to/file.py::ANY@sha256:ANY" --depth 0
```

### Hash Mismatch Recovery

If file on disk doesn't match DB hash:

```bash
# 1. Backup current file
cp path/to/file.py path/to/file.py.backup

# 2. Get DB hash
HASH=$(agentdb inventory | grep "path/to/file.py" | jq -r '.file_hash')

# 3. Calculate actual hash
ACTUAL=$(sha256sum path/to/file.py | awk '{print "sha256:"$1}')

# 4. If mismatch, re-ingest
if [ "$HASH" != "$ACTUAL" ]; then
  # Delete from DB (manual SQL)
  sqlite3 .agentdb/agent.sqlite "DELETE FROM files WHERE repo_path='path/to/file.py'"

  # Re-ingest
  agentdb ingest --path path/to/file.py < path/to/file.py.backup
fi
```

### Validation Utilities

```bash
# Validate AGTAG JSON
cat file.py | grep -A 100 "<!--AGTAG v1 START-->" | python3 -m json.tool

# Check DB integrity
sqlite3 .agentdb/agent.sqlite "PRAGMA integrity_check"

# View recent operations
sqlite3 .agentdb/agent.sqlite "SELECT * FROM ops_log ORDER BY ts DESC LIMIT 10"

# Check FTS index
sqlite3 .agentdb/agent.sqlite "SELECT COUNT(*) FROM symbols_fts"
```

---

## 📝 Contract Enforcement Summary

This system enforces contracts at multiple levels:

1. **Database constraints** (schema.sql): CHECK constraints on db_state
2. **CLI validation** (core.py): Rejects invalid states before execution
3. **AGTAG parsing** (core.py:43-54): JSON validation on every ingest/patch
4. **Hash verification** (core.py:202-204): Prevents concurrent modification
5. **This document**: Behavioral contracts for AI agents

**When in doubt**: Run `agentdb inventory` first, read error messages carefully, and consult this CLAUDE.md.
