# 🤖 Automatic Task Generation System

**Status:** ✅ OPERATIONAL | 🎯 Focus: CODE & TESTS | 🚫 NO Marketing BS

---

## 🎯 Purpose

Workers are **blazing fast** - they complete tasks faster than we can write them. This system **automatically generates** new tasks when the pool runs low, keeping workers busy indefinitely.

**Philosophy:** BULLETPROOF PRODUCT > Commercial deployment
- 50% Testing tasks (prove it works)
- 25% Code Quality tasks (make it maintainable)
- 15% Validation tasks (prove all claims with data)
- 7% Performance tasks (make it fast)
- 3% Refactoring tasks (keep it clean)

**NO documentation/deployment tasks** - those come AFTER the code is bulletproof.

---

## 📊 System Architecture

```
Pool Monitor (continuous loop)
    ↓
Check available tasks every 30s
    ↓
Available < 20? → Trigger Auto Generator
    ↓
Auto Generator analyzes codebase
    ↓
Generate 22 tasks:
    - 11 Testing tasks (TEST-XXX)
    - 6 Code Quality tasks (CODE-XXX)
    - 3 Validation tasks (VALID-XXX)
    - 1 Performance task (PERF-XXX)
    - 1 Refactoring task (REFACTOR-XXX)
    ↓
Tasks added to WORKER_TASK_QUEUE.json
    ↓
Workers claim and complete
    ↓
Loop continues forever
```

---

## 🔧 Components

### 1. Auto Task Generator (`scripts/auto_task_generator.py`)

**What it does:**
- Analyzes codebase to find untested files
- Identifies complex functions needing refactoring
- Creates testing, validation, and quality tasks
- Adds tasks to WORKER_TASK_QUEUE.json

**Task types generated:**

**TEST-XXX (50% of generation):**
- Test suites for untested files
- Integration tests for CLI workflows
- Stress tests (10K+ symbols)
- Edge case tests (malformed inputs)

**CODE-XXX (25% of generation):**
- Type annotation improvements
- Error handling enhancements
- Structured logging implementation

**VALID-XXX (15% of generation):**
- Architecture claim validation
- Database integrity validation
- Prove ALL claims with real data

**PERF-XXX (7% of generation):**
- Query optimization
- Memory leak detection
- Performance profiling

**REFACTOR-XXX (3% of generation):**
- Complexity reduction
- Dead code elimination

**Usage:**
```bash
# Manual trigger
.venv/bin/python3 scripts/auto_task_generator.py

# Force generation (ignore threshold)
.venv/bin/python3 << 'EOF'
from scripts.auto_task_generator import AutoTaskGenerator
generator = AutoTaskGenerator()
generator.generate_tasks(min_available=100)  # Force generation
EOF
```

### 2. Pool Monitor (`scripts/pool_monitor.py`)

**What it does:**
- Runs continuously in background
- Checks pool every 30 seconds
- Triggers generator when available < threshold
- Logs all activity

**Usage:**
```bash
# Run with defaults (threshold=20, interval=30s)
.venv/bin/python3 scripts/pool_monitor.py

# Run with custom threshold
.venv/bin/python3 scripts/pool_monitor.py --threshold 30 --interval 60

# Run in background
nohup .venv/bin/python3 scripts/pool_monitor.py > /tmp/pool_monitor.log 2>&1 &
```

**Output example:**
```
🔍 Pool Monitor Started
   Threshold: 20 available tasks
   Check interval: 30 seconds

[10:30:15] Available tasks: 38
✓ Pool healthy (38 >= 20)

[10:30:45] Available tasks: 18
⚠️  Below threshold (20)! Generating tasks...
✅ Generation complete. New count: 40
```

---

## 🚀 Real-World Example

**What just happened (2025-10-30):**

```
Initial state:
  Available: 38 tasks
  Threshold: 50 (forced for testing)

Auto-generator triggered:
  Analyzed codebase
  Found 10 untested files
  Generated 22 new tasks:
    ✅ TEST-001 to TEST-013 (13 testing tasks)
    ✅ CODE-001 to CODE-003 (3 code quality tasks)
    ✅ VALID-001 to VALID-002 (2 validation tasks)
    ✅ PERF-001 to PERF-002 (2 performance tasks)
    ✅ REFACTOR-001 to REFACTOR-002 (2 refactoring tasks)

Final state:
  Available: 60 tasks
  Workers: NEVER RUN OUT OF WORK!
```

**Generated tasks (examples):**

```
TEST-002: Create Test Suite for perfect_prompt_builder.py [high]
  - 90%+ code coverage
  - All functions tested
  - Edge cases covered
  - Estimated: 2.0 hours

CODE-002: Enhance Error Handling in Ingestion Pipeline [high]
  - Try-catch for all file operations
  - Detailed error messages
  - Graceful failure recovery
  - Estimated: 2.5 hours

VALID-001: Validate ALL Architecture Claims with Real Data [critical]
  - Every claim validated or marked false
  - Actual measurements vs claimed
  - NO unvalidated claims remain
  - Estimated: 4.0 hours

PERF-002: Memory Leak Detection and Prevention [critical]
  - Memory profiling under load
  - Leak detection and fixes
  - 24h stability test
  - Estimated: 2.5 hours
```

---

## ⚙️ Configuration

### Thresholds

**Pool Monitor:**
- Default: `min_threshold = 20`
- Recommended: 20-30 for steady work
- Aggressive: 40-50 for rapid development

**Auto Generator:**
- Generates ~22 tasks per run
- Configurable in `AutoTaskGenerator.__init__`

### Task Distribution

Modify in `auto_task_generator.py` (`generate_tasks` method):

```python
# Current distribution:
new_tasks.extend(self.generate_test_tasks(analysis))       # 50%
new_tasks.extend(self.generate_code_quality_tasks())      # 25%
new_tasks.extend(self.generate_validation_tasks())        # 15%
new_tasks.extend(self.generate_performance_tasks())       # 7%
new_tasks.extend(self.generate_refactoring_tasks())       # 3%

# To increase testing focus:
new_tasks.extend(self.generate_test_tasks(analysis))       # 70%
new_tasks.extend(self.generate_code_quality_tasks())      # 20%
# etc...
```

---

## 🎯 Key Principles

### 1. CODE & TESTS FIRST

**✅ Generates:**
- Test suites for untested files
- Integration tests
- Stress tests
- Edge case tests
- Code quality improvements
- Performance optimization
- Validation of claims

**❌ Does NOT generate:**
- Marketing documentation
- Commercial deployment tasks
- Sales materials
- User testimonials
- Feature requests without tests

### 2. PROVE EVERY CLAIM

Every generated VALID-XXX task validates architectural claims:

**Claim:** "97.3% token savings"
→ **Task:** VALID-001 measures 100+ symbols and proves it statistically

**Claim:** "95% backfill accuracy"
→ **Task:** Validate with A/B testing and ground truth

**Claim:** "Zero context loss"
→ **Task:** Multi-agent simulation proving it

**NO unvalidated claims in production.**

### 3. REAL MEASUREMENTS ONLY

**Generated validation tasks require:**
- ✅ Real data measurements (not estimates)
- ✅ Statistical significance (p < 0.05)
- ✅ Sample size >= 100
- ✅ Before/after comparisons
- ✅ Honest reporting (if claim fails, remove it)

**NO marketing BS allowed in generated tasks.**

---

## 🔍 Monitoring & Observability

### Check pool status

```bash
# Quick check
.venv/bin/agentdb pool status

# Show generated tasks
.venv/bin/agentdb pool status | grep -E "(TEST|CODE|VALID|PERF|REFACTOR)"

# Count by type
.venv/bin/agentdb pool status | grep -cE "TEST-"
.venv/bin/agentdb pool status | grep -cE "CODE-"
.venv/bin/agentdb pool status | grep -cE "VALID-"
```

### Monitor generation activity

```bash
# Watch pool monitor logs
tail -f /tmp/pool_monitor.log

# Watch task queue updates
watch -n 5 ".venv/bin/agentdb pool status | head -20"
```

### Verify generation quality

```bash
# List all auto-generated tasks
.venv/bin/python3 << 'EOF'
import json
with open('WORKER_TASK_QUEUE.json') as f:
    data = json.load(f)
auto_tasks = [t for t in data['tasks'] if t.get('auto_generated')]
print(f"Auto-generated: {len(auto_tasks)} tasks")
for task in auto_tasks[:10]:
    print(f"  {task['task_id']}: {task['title']}")
EOF
```

---

## 🚀 Production Deployment

### Run pool monitor as systemd service

Create `/etc/systemd/system/agentdb-pool-monitor.service`:

```ini
[Unit]
Description=AgentDB Pool Monitor
After=network.target

[Service]
Type=simple
User=gontrand
WorkingDirectory=/home/gontrand/ActiveProjects/agentdb-mvp
ExecStart=/home/gontrand/ActiveProjects/agentdb-mvp/.venv/bin/python3 scripts/pool_monitor.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable agentdb-pool-monitor
sudo systemctl start agentdb-pool-monitor
sudo systemctl status agentdb-pool-monitor
```

### Run as cron job (alternative)

```bash
# Edit crontab
crontab -e

# Add this line (check every 5 minutes)
*/5 * * * * cd /home/gontrand/ActiveProjects/agentdb-mvp && .venv/bin/python3 scripts/auto_task_generator.py >> /tmp/auto_gen.log 2>&1
```

---

## 📊 Statistics & Impact

**Before auto-generation:**
- 57 manual tasks
- Workers run out of work
- Context window underutilized
- Development slows down

**After auto-generation:**
- 79 total tasks (57 manual + 22 auto)
- Workers NEVER idle
- Context window fully utilized
- Development accelerates

**Expected with continuous monitoring:**
- Pool maintained at 20-40 available tasks
- Infinite work for infinite workers
- Systematic code quality improvement
- All claims validated with real data

---

## 🎯 Next Steps

**System is operational - workers have infinite work!**

**To start continuous monitoring:**
```bash
# Terminal 1: Start pool monitor
.venv/bin/python3 scripts/pool_monitor.py

# Terminal 2: Watch activity
watch -n 10 ".venv/bin/agentdb pool status | head -30"

# Terminal 3: Monitor workers
tail -f .agentdb/pool_activity.log
```

**Workers will now:**
1. ✅ Never run out of tasks
2. ✅ Focus on testing and code quality
3. ✅ Validate all architectural claims
4. ✅ Build a bulletproof product

---

## 🏆 Success Criteria

**This system succeeds when:**

✅ Pool NEVER drops below 20 available tasks
✅ 90%+ of generated tasks are testing/code quality
✅ ALL architectural claims validated with real data
✅ NO marketing BS in generated tasks
✅ Workers continuously busy
✅ Product is BULLETPROOF before deployment

**The goal: Build a product so solid that marketing writes itself from the test results.**

---

**Auto-generation system: OPERATIONAL 🚀**
**Focus: CODE & TESTS > Everything else**
**Result: Infinite high-quality work for workers**
