# 🚨 CRITICAL INCIDENT: worker_pool.py Corruption

**Date:** 2025-10-30
**Severity:** CRITICAL
**Status:** FILE CORRUPTED | RECOVERY REQUIRED

---

## Incident Summary

**File Corrupted:** `src/agentdb/worker_pool.py`
**Original Size:** ~20KB+ (estimated)
**Current Size:** 23 bytes (shebang only)
**Cause:** Worker attempted to fix AGTAG blocks using sed commands
**Git Backup:** NOT AVAILABLE (no git repository!)

---

## What Happened

1. Worker claimed task SIMPLE-002: "List and Catalog All Project Files"
2. Worker attempted to fix AGTAG syntax issues in Python files
3. Worker used sed commands to modify AGTAG blocks
4. sed commands corrupted worker_pool.py (reduced to 23 bytes)
5. Potentially corrupted other files (assessment needed)

---

## Current File State

```bash
$ cat src/agentdb/worker_pool.py
#!/usr/bin/env python3

$ wc -c src/agentdb/worker_pool.py
23 src/agentdb/worker_pool.py
```

**Contents:** Only shebang line remains. All functionality lost.

---

## Impact Assessment

**Immediate Impact:**
- worker_pool.py functionality LOST
- Worker pool coordination BROKEN (if this file was in use)
- SIMPLE-002 task CANNOT complete
- Worker session STOPPED

**System-Wide Impact:**
- ✅ Core agentdb CLI still functional (worker_pool.py not imported)
- ✅ Task queue system still operational (uses WORKER_TASK_QUEUE.json)
- ✅ Other workers can continue (if they avoid AGTAG tasks)
- ⚠️ Unknown number of other files potentially corrupted

---

## Related to AGTAG Syntax Issue

**This is the SECOND incident caused by AGTAG format incompatibility!**

**Incident #1 (Earlier today):**
- Worker REVIEW-009: Added invalid AGTAG blocks to 128 Python files
- Broke Python imports (HTML comment syntax invalid)
- Corrupted src/agentdb/*.py files

**Incident #2 (Current):**
- Worker SIMPLE-002: Attempted to FIX AGTAG blocks with sed
- sed commands corrupted worker_pool.py
- File now 23 bytes (completely wiped)

**Pattern:** Workers trying to work with AGTAG blocks are causing catastrophic failures.

---

## Root Cause Analysis

### Why This Happened

1. **AGTAG Format Incompatibility:** HTML comments not valid in Python
2. **Incomplete Documentation:** CLAUDE.md didn't specify file-type formats (now fixed)
3. **No Validation:** No pre-flight checks for AGTAG syntax
4. **Dangerous sed Usage:** sed commands can corrupt files if regex is wrong
5. **No Backups:** No git repository for recovery
6. **Auto-Generated Tasks:** System generating AGTAG-related tasks that cause issues

### Specific sed Command Failure

Worker likely ran something like:
```bash
sed -i 's/<!--AGTAG/AGTAG_METADATA = """<!--AGTAG/' file.py
```

**Problem:** If regex matches incorrectly, sed can:
- Delete entire file contents
- Leave only fragments
- Corrupt binary data
- Break Python syntax even worse

**Result:** worker_pool.py reduced to shebang line only.

---

## Recovery Options

### Option 1: Restore from Git (NOT AVAILABLE)
```bash
git checkout src/agentdb/worker_pool.py
```

**Status:** ❌ No git repository exists

### Option 2: Restore from Backup (NOT AVAILABLE)
```bash
cp /backup/worker_pool.py src/agentdb/worker_pool.py
```

**Status:** ❌ No backup found

### Option 3: Recreate from Specification (POSSIBLE)
```bash
# Worker pool functionality requirements:
# - Task claiming with atomic file locking
# - Worker registration and heartbeat
# - Task status updates
# - Pool statistics
```

**Status:** ✅ Can recreate if specification exists
**Effort:** 4-8 hours development time

### Option 4: Accept Loss (IF NOT CRITICAL)
```bash
# If worker_pool.py wasn't actively used:
# - Delete corrupted file
# - Remove from codebase
# - Update documentation
```

**Status:** ✅ Viable if feature not in use (no imports found)
**Effort:** 15 minutes cleanup

---

## Immediate Actions Required

### 1. STOP All AGTAG-Related Tasks

**Update WORKER_TASK_QUEUE.json:**
```json
{
  "task_id": "REVIEW-009",
  "status": "blocked",
  "blocker": "AGTAG syntax incompatibility - PAUSED until hybrid system implemented"
}
```

**Update Auto-Generator:**
```python
# In scripts/auto_task_generator.py
BLOCKED_TASK_TYPES = [
    "agtag_generation",
    "agtag_modification",
    "agtag_syntax_fix"
]

def generate_tasks(...):
    # SKIP any AGTAG-related tasks
    if "agtag" in task_description.lower():
        return []  # Don't generate until safe
```

### 2. Assess Other File Damage

**Scan for corrupted files:**
```bash
# Find suspiciously small Python files
find . -name "*.py" -type f -size -1k -not -path "./.venv/*"

# Check if they're stub files or corrupted
for file in $(find . -name "*.py" -size -1k); do
    echo "$file: $(wc -l < "$file") lines"
done
```

### 3. Update CLAUDE.md with CRITICAL WARNING

**Add to top of file:**
```markdown
🚨 CRITICAL: AGTAG TASKS TEMPORARILY DISABLED

Due to two corruption incidents (REVIEW-009, SIMPLE-002), ALL tasks
involving AGTAG block modification are PAUSED until hybrid LLM-parser
system is implemented.

DO NOT:
- ❌ Generate AGTAG blocks for Python files
- ❌ Modify existing AGTAG blocks with sed/awk
- ❌ Create tasks that touch AGTAG syntax

WAIT FOR:
- ✅ LLM-parser system (in progress)
- ✅ Validation tools (available: tools/validate_agtag_syntax.py)
- ✅ Safer AGTAG workflow
```

### 4. Update Pool Monitor

**Prevent AGTAG task generation:**
```python
# In scripts/pool_monitor.py
TASK_GENERATION_PAUSED = True  # Manual override

# In scripts/auto_task_generator.py
if TASK_GENERATION_PAUSED:
    print("⚠️  Task generation PAUSED due to AGTAG incidents")
    return 0
```

---

## worker_pool.py Recovery Strategy

### Assess Criticality

**Question:** Is worker_pool.py actively used?

**Check:**
```bash
# No imports found:
$ grep -r "import.*worker_pool" . --include="*.py"
# (no output)

# Check WORKER_CONTEXT.md references:
$ grep -i "worker_pool" *.md
WORKER_CONTEXT.md: "Worker pool system uses fcntl locking"
```

**Conclusion:** File was PLANNED but may not be implemented yet.

### Decision Matrix

| Option | Effort | Risk | Outcome |
|--------|--------|------|---------|
| **Recreate from spec** | High (4-8h) | Low | Fully functional |
| **Restore from backup** | N/A | N/A | Not available |
| **Accept loss** | Low (15min) | Low | Feature removed |
| **Stub placeholder** | Low (30min) | Medium | Documented TODO |

### Recommended: Stub Placeholder

**Recreate as stub with TODO:**

```python
#!/usr/bin/env python3
"""
Worker Pool Coordinator - FILE CORRUPTED 2025-10-30

This file was corrupted during incident SIMPLE-002 when a worker
attempted to fix AGTAG blocks using sed commands.

Original functionality (PLANNED):
- Atomic task claiming with fcntl locking
- Worker registration and heartbeat
- Task status updates via WORKER_TASK_QUEUE.json
- Pool statistics and monitoring

Current Status: STUB - awaiting reimplementation

Replacement System (IN USE):
- WORKER_TASK_QUEUE.json (manual file locking)
- scripts/pool_monitor.py (auto task generation)
- scripts/auto_task_generator.py (task creation)

TODO:
- [ ] Recreate worker_pool.py with proper specification
- [ ] Add atomic file locking (fcntl)
- [ ] Add worker registration/heartbeat
- [ ] Add comprehensive tests

Related Incidents:
- INCIDENT_REPORT_AGTAG_SYNTAX_FAILURE.md
- INCIDENT_REPORT_FILE_CORRUPTION_WORKER_POOL.md

Recovery blocked until hybrid LLM-parser system implemented.
"""

# Stub imports for compatibility
import fcntl
import json
from pathlib import Path
from typing import Dict, List, Optional

class WorkerPool:
    """
    Stub class - original implementation lost during corruption incident.

    DO NOT USE until reimplemented.
    """

    def __init__(self):
        raise NotImplementedError(
            "WorkerPool corrupted during incident SIMPLE-002. "
            "See INCIDENT_REPORT_FILE_CORRUPTION_WORKER_POOL.md for details."
        )

# TODO: Reimplement based on specification
```

**Benefits:**
- Documents what was lost
- Prevents import errors
- Provides clear error message
- Tracks recovery progress

---

## Long-Term Prevention

### 1. Implement Hybrid LLM-Parser System (URGENT)

**Status:** Design complete (ARCHITECTURE_DECISION_AGTAG_VS_LLM_PARSER.md)

**Timeline:**
- Week 1: Build llm_analyzer.py
- Week 2: Add --llm-analyze flag
- Week 3: Test and validate
- Week 4: Deploy as default

**Impact:** Eliminates ALL AGTAG syntax issues by avoiding file modification

### 2. Add File Operation Safety Checks

**Create:** `tools/safe_edit.py`

```python
def safe_edit(file_path: str, operation: str):
    """
    Safely edit file with automatic backup and validation.

    Args:
        file_path: File to edit
        operation: sed/awk/python command

    Returns:
        Success/failure with rollback on error
    """
    # 1. Create backup
    backup_path = f"{file_path}.backup.{datetime.now().timestamp()}"
    shutil.copy(file_path, backup_path)

    try:
        # 2. Apply operation
        result = subprocess.run(operation, shell=True, check=True)

        # 3. Validate result (check file size, syntax, etc.)
        if validate_edit(file_path):
            os.remove(backup_path)
            return True
        else:
            # Rollback on validation failure
            shutil.copy(backup_path, file_path)
            return False

    except Exception as e:
        # Rollback on exception
        shutil.copy(backup_path, file_path)
        raise
```

### 3. Enable Git Repository (CRITICAL)

**Initialize git:**
```bash
cd /home/gontrand/ActiveProjects/agentdb-mvp
git init
git add .
git commit -m "Initial commit before AGTAG incidents"

# Create branch for experiments
git checkout -b experimental-agtag-fixes
```

**Benefits:**
- Version control for all changes
- Easy rollback on corruption
- History of what was lost
- Diff tracking for debugging

### 4. Add Pre-Flight Validation

**Before ANY file modification:**
```bash
# 1. Validate syntax BEFORE editing
python3 -m py_compile file.py  # For Python files

# 2. Run safe_edit.py wrapper
python3 tools/safe_edit.py --file file.py --operation "sed 's/.../.../'"

# 3. Validate AFTER editing
python3 -m py_compile file.py  # Ensure still valid
```

### 5. Update Auto-Generator Safeguards

**Add to `scripts/auto_task_generator.py`:**

```python
UNSAFE_OPERATIONS = [
    "sed -i",  # In-place sed (dangerous)
    "awk -i",  # In-place awk
    "rm -rf",  # Recursive delete
    "dd",      # Direct disk write
]

def validate_task_safety(task: Dict) -> bool:
    """Validate task doesn't include dangerous operations."""
    description = task.get("description", "").lower()

    for unsafe_op in UNSAFE_OPERATIONS:
        if unsafe_op in description:
            return False

    return True

def generate_tasks(...):
    new_tasks = []

    # ... generation logic ...

    # Filter unsafe tasks
    new_tasks = [t for t in new_tasks if validate_task_safety(t)]

    return new_tasks
```

---

## Summary

**Incident:** worker_pool.py corrupted (23 bytes remaining)
**Cause:** sed commands during AGTAG syntax fix attempt
**Related:** Second incident caused by AGTAG format issues
**Recovery:** Stub file + TODO for reimplementation
**Prevention:** Hybrid LLM-parser system + git + validation

**CRITICAL:** All AGTAG-related tasks must be PAUSED until hybrid system operational.

---

## Status

- ✅ worker_pool.py damage assessed
- ✅ Corruption cause identified (sed during AGTAG fix)
- ✅ Incident documented
- 🔄 Recovery strategy defined (stub + TODO)
- 🔄 Prevention measures designed
- ⏸️ AGTAG tasks PAUSED until safe

**Next Steps:**
1. Create worker_pool.py stub
2. Scan for other corrupted files
3. Update CLAUDE.md with CRITICAL warning
4. Pause auto-generator AGTAG task creation
5. Initialize git repository
6. Implement hybrid LLM-parser system (eliminate AGTAG issues permanently)
