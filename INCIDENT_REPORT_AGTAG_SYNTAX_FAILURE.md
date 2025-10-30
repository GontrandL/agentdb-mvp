# 🚨 Incident Report: AGTAG Syntax Failure in Python Files

**Date:** 2025-10-30
**Severity:** CRITICAL
**Status:** ROOT CAUSE IDENTIFIED | FIX REQUIRED

---

## Executive Summary

A worker attempting task REVIEW-009 ("Generate AGTAGs for All Files Without Tags") caused a cascading failure by adding AGTAG blocks with invalid Python syntax to 128 dashboard files and src/ files. The agentdb CLI is now broken.

**Root Cause:** Incomplete/misleading documentation in CLAUDE.md
**Impact:** Core system broken, cannot complete tasks
**Tasks Affected:** REVIEW-009 (completed with errors), TEST-001 (blocked)

---

## Timeline of Events

1. **Worker claims REVIEW-009:** "Generate AGTAGs for All Files Without Tags"
2. **Worker adds AGTAGs to 128 files** including Python files in dashboard/ and src/
3. **Syntax error occurs:** HTML comment markers `<!--` break Python imports
4. **Worker attempts fix:** Tries wrapping in docstrings (fails)
5. **Cleanup script runs:** Over-deletes and corrupts src/agentdb/*.py files
6. **System broken:** agentdb CLI cannot run, tasks blocked
7. **Worker session ends:** Reports critical failure and requests investigation

---

## Root Cause Analysis

### The Documentation Bug

**CLAUDE.md (lines 113-119) shows this format:**
```
<!--AGTAG v1 START-->
{"version":"v1","symbols":[...],"docs":[...],"tests":[...]}
<!--AGTAG v1 END-->
```

**Critical omission:** This format is ONLY valid for:
- ✅ HTML files
- ✅ Markdown files
- ❌ **NOT Python files!**

### The Correct Format (For Python)

**examples/example.py (lines 5-8) shows the CORRECT format:**
```python
AGTAG_METADATA = """<!--AGTAG v1 START-->
{"version":"v1","symbols":[{"path":"src/example.py","name":"example"...}]}
<!--AGTAG v1 END-->
"""
```

**Key difference:**
- HTML comments MUST be wrapped in `AGTAG_METADATA = """..."""`
- This makes them a Python string literal (valid syntax)
- Without the wrapper, `<!--` is invalid Python and breaks imports

### Why the Worker Made This Mistake

**CLAUDE.md never mentions `AGTAG_METADATA` variable!**

```bash
$ grep -c "AGTAG_METADATA" CLAUDE.md
0  # ← ZERO occurrences!
```

The worker followed the documented format exactly, but the documentation was incomplete for Python files.

---

## Technical Details

### Invalid Syntax (What Worker Did)

```python
# src/agentdb/core.py (BROKEN)
import json
import sqlite3

<!--AGTAG v1 START-->  # ← Python syntax error!
{"version":"v1","symbols":[...]}
<!--AGTAG v1 END-->
```

**Error:**
```
SyntaxError: invalid syntax
  File "src/agentdb/core.py", line 3
    <!--AGTAG v1 START-->
       ^
```

### Valid Syntax (What Should Have Been Done)

```python
# src/agentdb/core.py (CORRECT)
import json
import sqlite3

# ... actual code ...

AGTAG_METADATA = """<!--AGTAG v1 START-->
{"version":"v1","symbols":[...]}
<!--AGTAG v1 END-->
"""
```

**Result:** Valid Python, AGTAG parsable as string content

---

## Impact Assessment

### Files Corrupted
- **128 total files** had invalid AGTAGs added
- **Dashboard files:** ~120 files with broken Python syntax
- **Core src/ files:** ~8 files in src/agentdb/ corrupted
- **CLI broken:** agentdb command cannot execute

### Tasks Affected

**REVIEW-009:** "Generate AGTAGs for All Files Without Tags"
- Status: "completed" (but with catastrophic errors)
- Result: 128 files corrupted instead of properly tagged

**TEST-001:** "Create Test Suite for doc_zoom.py"
- Status: Test suite created but cannot run
- Blocker: Broken imports due to AGTAG syntax errors

**Future Tasks:** Any task involving AGTAG generation on Python files

### System State

**Before incident:**
- ✅ agentdb CLI functional
- ✅ All tests passing (65/66)
- ✅ 170 dashboard files successfully ingested

**After incident:**
- ❌ agentdb CLI broken (import errors)
- ❌ Tests cannot run (broken dependencies)
- ❌ Core system unusable

---

## Why This Wasn't Caught Earlier

### examples/example.py Uses Correct Format
But workers don't always read examples - they read CLAUDE.md (system prompt)

### tests/ Don't Validate AGTAG Python Syntax
No test verifies that AGTAGs in Python files use `AGTAG_METADATA` wrapper

### No Safeguard in Auto-Generator
Auto-generator doesn't check file extension before suggesting AGTAG format

### CLAUDE.md Doesn't Distinguish by File Type
Shows one universal format instead of format-per-language

---

## Proposed Fixes

### 1. Update CLAUDE.md Documentation (CRITICAL)

**Add section:**
```markdown
### AGTAG Format by File Type

**For HTML/Markdown files (.html, .md):**
```
<!--AGTAG v1 START-->
{"version":"v1","symbols":[...]}
<!--AGTAG v1 END-->
```

**For Python files (.py):**
```python
AGTAG_METADATA = """<!--AGTAG v1 START-->
{"version":"v1","symbols":[...]}
<!--AGTAG v1 END-->
"""
```

**Why:** HTML comments are not valid Python syntax. The AGTAG_METADATA variable makes them a string literal.
```

### 2. Add Validation to Auto-Generator

**In `scripts/auto_task_generator.py`:**
```python
def generate_test_tasks(self, analysis: Dict) -> List[Dict]:
    for untested_file in analysis['untested_files']:
        # ... existing code ...

        # SAFEGUARD: If task involves AGTAG on Python files
        if untested_file.endswith('.py'):
            deliverables.append(
                "AGTAGs wrapped in AGTAG_METADATA = '''...''' (Python syntax)"
            )
```

### 3. Create AGTAG Syntax Validator

**New tool:** `tools/validate_agtag_syntax.py`
```python
def validate_agtag_syntax(file_path: str) -> bool:
    """Validate AGTAG has correct syntax for file type."""
    if file_path.endswith('.py'):
        # Python: Must have AGTAG_METADATA wrapper
        content = open(file_path).read()
        if '<!--AGTAG v1 START-->' in content:
            if 'AGTAG_METADATA' not in content:
                return False  # Missing wrapper!
    return True
```

### 4. Add Pre-Ingest Validation

**In `src/agentdb/core.py` (ingest command):**
```python
def ingest_file(repo_path: str, content: str):
    # Existing code...

    # NEW: Validate AGTAG syntax for Python files
    if repo_path.endswith('.py'):
        if '<!--AGTAG' in content and 'AGTAG_METADATA' not in content:
            raise ValueError(
                f"Invalid AGTAG format for Python file {repo_path}. "
                "Python files must wrap AGTAG in AGTAG_METADATA = '''...'''")
```

### 5. Update Task REVIEW-009 Description

**Current:** "Generate AGTAGs for All Files Without Tags"

**Updated:**
```
Generate AGTAGs for All Files Without Tags

CRITICAL: Use correct format based on file type:
- .py files: AGTAG_METADATA = """<!--AGTAG v1 START-->..."""
- .md/.html files: <!--AGTAG v1 START-->... (direct)

Validate syntax before ingesting!
```

---

## Recovery Steps

### Immediate (Required)

1. **Restore src/agentdb/*.py from git/backup**
   ```bash
   git checkout src/agentdb/*.py  # If using git
   # OR restore from backup
   ```

2. **Remove invalid AGTAGs from dashboard files**
   ```bash
   # Find files with invalid AGTAGs (Python files with direct HTML comments)
   find dashboard -name "*.py" -exec grep -l "^<!--AGTAG" {} \;

   # Remove invalid AGTAG blocks
   # (Manual review needed - auto-removal risky)
   ```

3. **Verify CLI works**
   ```bash
   agentdb --help  # Should not error
   agentdb inventory  # Should show files
   ```

4. **Re-run tests**
   ```bash
   pytest -q  # Verify 65+ tests pass
   ```

### Medium-term (This Week)

5. **Update CLAUDE.md** with file-type-specific AGTAG formats

6. **Add AGTAG syntax validator** to tools/

7. **Update auto-generator** with safeguards

8. **Re-process REVIEW-009** correctly:
   ```bash
   # Create new task: REVIEW-009-FIX
   # Use correct AGTAG format per file type
   # Validate before ingesting
   ```

### Long-term (Prevent Recurrence)

9. **Add integration test** that validates AGTAG syntax:
   ```python
   def test_agtag_syntax_by_file_type():
       """Ensure Python files use AGTAG_METADATA wrapper."""
       for py_file in glob('**/*.py'):
           content = open(py_file).read()
           if '<!--AGTAG' in content:
               assert 'AGTAG_METADATA' in content
   ```

10. **Create AGTAG generation tool** that auto-formats correctly:
    ```bash
    tools/generate_agtag.py --file src/example.py
    # Auto-detects .py extension
    # Uses AGTAG_METADATA wrapper automatically
    ```

---

## Lessons Learned

### Documentation is Critical

**Problem:** CLAUDE.md is the system prompt - if it's wrong, ALL workers make the same mistake

**Solution:**
- Review CLAUDE.md for completeness
- Add file-type-specific instructions
- Include examples for each language

### Validation Before Ingestion

**Problem:** Invalid AGTAGs were ingested without validation

**Solution:**
- Add pre-ingest syntax validation
- Reject files with invalid AGTAG format
- Provide clear error messages

### Auto-Generator Needs Safeguards

**Problem:** Could generate tasks that cause the same issue

**Solution:**
- File-type awareness in task generation
- Include correct format in task deliverables
- Add validation requirements to task descriptions

### Test Coverage Gaps

**Problem:** No tests validate AGTAG syntax correctness

**Solution:**
- Add integration tests for AGTAG syntax
- Validate each file type (Python, HTML, Markdown)
- Run validation in CI/CD

---

## Prevention Checklist

Before ANY task involving AGTAG generation:

- [ ] Check file extension (.py, .md, .html)
- [ ] Use correct format for file type:
  - [ ] Python: `AGTAG_METADATA = """..."""`
  - [ ] Markdown/HTML: Direct HTML comments
- [ ] Validate syntax before ingesting
- [ ] Test import succeeds (for Python files)
- [ ] Run pytest to verify no breakage

---

## Action Items

**IMMEDIATE (Today):**
- [ ] Restore src/agentdb/*.py files (git checkout or backup)
- [ ] Update CLAUDE.md with file-type-specific AGTAG formats
- [ ] Create AGTAG syntax validator tool
- [ ] Test agentdb CLI works

**THIS WEEK:**
- [ ] Update auto-generator with safeguards
- [ ] Add AGTAG syntax validation to ingest command
- [ ] Create integration test for AGTAG syntax
- [ ] Re-process REVIEW-009 correctly

**ONGOING:**
- [ ] Review all auto-generated task descriptions
- [ ] Add format validation to worker instructions
- [ ] Monitor for similar issues in future tasks

---

## Conclusion

**Root Cause:** Incomplete CLAUDE.md documentation led worker to use invalid AGTAG syntax in Python files

**Impact:** Critical - 128 files corrupted, CLI broken, tasks blocked

**Fix Complexity:** Medium - restore files, update docs, add validation

**Recurrence Risk:** LOW after fixes implemented (validation + updated docs)

**Estimated Recovery Time:** 2-4 hours

---

## References

- **CLAUDE.md:** Lines 113-119 (incomplete AGTAG documentation)
- **examples/example.py:** Lines 5-8 (correct Python AGTAG format)
- **src/agentdb/agtag.py:** Lines 35 (AGTAG_METADATA variable)
- **Task REVIEW-009:** "Generate AGTAGs for All Files Without Tags"
- **Worker Report:** Session ended with critical failure notification

---

**Status:** Investigation complete | Fixes pending | Recovery plan ready

**Recommendation:** Implement immediate fixes before allowing further AGTAG-related tasks.
