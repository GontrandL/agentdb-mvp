#!/usr/bin/env python3

Delegate Phase 2 + Critical Gaps Package to Z.AI

Delegates 18 hours of work in parallel:
- Phase 2 HIGH: Environment Status, Context Generator, Dynamic CLAUDE.md
- Gap Closure: Intelligence Integration, Sentinel completion, Stability

This preserves Claude's token budget for reviews only (~5K tokens vs 50K+ for direct implementation).


import sys
import json
from pathlib import Path

# Add dashboard to path
sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))

from cli.delegate_to_z_ai import ZAIDelegator


def create_phase2_tasks():
    """Define Phase 2 + Gap closure tasks for Z.AI."""

    tasks = [
        # === PHASE 2 HIGH PRIORITY (8 hours) ===

        {
            "id": "phase2-a1",
            "title": "Environment Status Provider",
            "priority": "high",
            "estimated_hours": 2,
            "description": """
Build EnvironmentStatusProvider class that provides real-time environment health.

Requirements:
1. Query Core AgentDB (.agentdb/agent.sqlite) for symbol counts
2. Query Dashboard DB (agentdb.db) for file coverage stats
3. Check autonomous_gaps table for error patterns
4. Return system health, recent activity, error patterns, resource usage
5. Return structured dict (NO markdown generation)

Deliverable: dashboard/app/utils/environment_status.py (200 lines)

Must include:
- get_live_environment_context() method
- Database connection management
- Error handling for missing databases
- Comprehensive status dict with all sections

See Z_AI_PHASE2_PLUS_GAPS.md Task A1 for detailed specifications.
            """,
            "validation": """
python3 -c "
from dashboard.app.utils.environment_status import EnvironmentStatusProvider
env = EnvironmentStatusProvider()
status = env.get_live_environment_context()
assert 'system_health' in status
assert 'recent_activity' in status
assert status['system_health']['coverage_percentage'] >= 0.0
print('✅ EnvironmentStatusProvider validation passed')
"
            """,
            "deliverables": [
                "dashboard/app/utils/environment_status.py"
            ]
        },

        {
            "id": "phase2-a2",
            "title": "Project Context Generator",
            "priority": "high",
            "estimated_hours": 3,
            "description": """
Build ProjectContextGenerator that creates optimized session context packs.

Requirements:
1. Use EnvironmentStatusProvider for environment data
2. Query autonomous_gaps for current issues
3. Query architectural_patterns table for project patterns
4. Query session_messages for similar past tasks
5. Extract successful patterns from evidence_packs
6. Generate context < 5000 tokens total
7. Support task_type filtering ('code_fixer', 'feature_builder', etc.)

Deliverable: dashboard/app/context/project_context_generator.py (350 lines)

Must include:
- build_session_context(task_type, target_files) method
- Integration with EnvironmentStatusProvider
- Database queries for intelligence sources
- Token budget optimization (< 5000 tokens)
- Progressive disclosure (L0/L1 for most items)

See Z_AI_PHASE2_PLUS_GAPS.md Task A2 for detailed specifications.
            """,
            "validation": """
python3 -c "
from dashboard.app.context.project_context_generator import ProjectContextGenerator
generator = ProjectContextGenerator()
context = generator.build_session_context('code_fixer', ['src/agentdb/core.py'])
assert context['token_budget']['context_size'] < 5000
assert len(context['active_rules']) > 0
assert 'environment_status' in context
print('✅ ProjectContextGenerator validation passed')
"
            """,
            "deliverables": [
                "dashboard/app/context/project_context_generator.py"
            ]
        },

        {
            "id": "phase2-a3",
            "title": "Dynamic CLAUDE.md Generator",
            "priority": "high",
            "estimated_hours": 3,
            "description": """
Build DynamicCLAUDEGenerator that generates live CLAUDE.md with project intelligence.

Requirements:
1. Create Jinja2 template for CLAUDE.md structure
2. Use ProjectContextGenerator for context data
3. Use EnvironmentStatusProvider for health data
4. Query evidence_packs for successful patterns
5. Include static rules + live project intelligence
6. Optimize for < 8000 tokens
7. Support task-specific guidance

Deliverables:
- dashboard/app/context/dynamic_claude_md.py (250 lines)
- dashboard/templates/claude_md_template.md.j2 (100 lines)

Must include:
- generate_dynamic_claude(task_type, instance_id) method
- Jinja2 template with all required sections
- Integration with ProjectContextGenerator
- Token budget checking
- Markdown formatting

See Z_AI_PHASE2_PLUS_GAPS.md Task A3 for detailed specifications.
            """,
            "validation": """
python3 -c "
from dashboard.app.context.dynamic_claude_md import DynamicCLAUDEGenerator
generator = DynamicCLAUDEGenerator()
claude_md = generator.generate_dynamic_claude(task_type='code_fixer')
assert len(claude_md) > 0
assert 'Current Project State' in claude_md
assert 'Active Gaps' in claude_md
token_count = len(claude_md.split()) * 1.3
assert token_count < 8000
print('✅ DynamicCLAUDEGenerator validation passed')
"
            """,
            "deliverables": [
                "dashboard/app/context/dynamic_claude_md.py",
                "dashboard/templates/claude_md_template.md.j2"
            ]
        },

        # === CRITICAL GAP CLOSURE (10 hours) ===

        {
            "id": "gap-b1",
            "title": "Intelligence Integrator",
            "priority": "critical",
            "estimated_hours": 4,
            "description": """
Build IntelligenceIntegrator that connects ALL existing intelligence systems.

Intelligence Sources to Query:
1. session_messages (25,000+ interactions) - historical patterns
2. trace_events (decision history) - successful traces
3. evidence_packs (solution documentation) - what worked
4. architectural_patterns (project rules) - conventions
5. autonomous_gaps (current issues) - priorities
6. tool_violations (compliance history) - mistakes to avoid

Requirements:
1. Query all 6 intelligence sources
2. Extract patterns from session history
3. Mine evidence packs for successful approaches
4. Get compliance patterns from violations
5. Merge all sources into enriched context
6. 4x richer context than base

Deliverable: dashboard/app/context/intelligence_integrator.py (400 lines)

Must include:
- enhance_context_with_existing_data() method
- _get_session_history_patterns() implementation
- _extract_successful_patterns() from evidence_packs
- _get_compliance_patterns() from violations
- _merge_intelligence_sources() algorithm
- Database connection management

See Z_AI_PHASE2_PLUS_GAPS.md Task B1 for detailed SQL queries and specifications.
            """,
            "validation": """
python3 -c "
from dashboard.app.context.intelligence_integrator import IntelligenceIntegrator
integrator = IntelligenceIntegrator(dashboard_db='dashboard/agentdb.db')
enhanced = integrator.enhance_context_with_existing_data(
    base_context={'files': ['src/agentdb/core.py']},
    task_type='code_fixer',
    instance_id='test_instance'
)
assert 'historical_patterns' in enhanced
assert 'successful_approaches' in enhanced
assert 'compliance_patterns' in enhanced
assert len(enhanced.keys()) >= 10
print('✅ IntelligenceIntegrator validation passed')
"
            """,
            "deliverables": [
                "dashboard/app/context/intelligence_integrator.py"
            ]
        },

        {
            "id": "gap-b2",
            "title": "Complete Sentinel MCP Services",
            "priority": "high",
            "estimated_hours": 3,
            "description": """
Complete 15 TODOs in Sentinel MCP to fully utilize framework.

Priority TODOs:
1. Line 631: context_diff implementation
2. Lines 671-673: Real metrics (OCR queue, eventbus, watchdog)
3. Line 1027: Violations table query
4. Line 1071: Heartbeat storage
5. Line 1121: Support bundle generation
... and 10 more TODOs

Requirements:
1. Implement all missing methods marked with TODO
2. Add missing database tables (instance_heartbeats)
3. Connect to existing intelligence sources
4. Add proper error handling
5. Write tests for each completed service

Files to modify:
- dashboard/app/mcp/sentinel.py (complete TODOs)
- dashboard/migrations/015_heartbeats.sql (new table)

See Z_AI_PHASE2_PLUS_GAPS.md Task B2 for detailed implementations.
            """,
            "validation": """
python3 -c "
from dashboard.app.mcp.sentinel import SentinelMCP
sentinel = SentinelMCP(dashboard_db='dashboard/agentdb.db')

# Test completed services
diff = sentinel.context_diff(['item1'], ['item2'])
assert 'added_count' in diff

metrics = sentinel._get_real_metrics()
assert 'ocr_queue_size' in metrics

violations = sentinel._get_violations_from_db('test_instance')
assert isinstance(violations, list)

print('✅ Sentinel MCP completion validation passed')
"
            """,
            "deliverables": [
                "dashboard/app/mcp/sentinel.py",
                "dashboard/migrations/015_heartbeats.sql"
            ]
        },

        {
            "id": "gap-b3",
            "title": "Service Stability Enhancement",
            "priority": "high",
            "estimated_hours": 2,
            "description": """
Add connection pooling and unified caching for maximum stability.

Requirements:
1. Build ConnectionManager class with SQLite connection pooling
2. Build UnifiedCache class with TTL-based caching
3. Support thread-safe operations
4. Provide singleton instances for all services
5. Add cache invalidation support

Deliverables:
- dashboard/app/db/connection_manager.py (150 lines)
- dashboard/app/cache/unified_cache.py (120 lines)

Must include:
- ConnectionManager with pool_size parameter
- get_connection() and release_connection() methods
- UnifiedCache with TTL expiration
- Thread-safe locking
- Singleton instances for dashboard and core DBs

See Z_AI_PHASE2_PLUS_GAPS.md Task B3 for detailed specifications.
            """,
            "validation": """
python3 -c "
from dashboard.app.db.connection_manager import ConnectionManager, dashboard_conn_manager
from dashboard.app.cache.unified_cache import UnifiedCache, intelligence_cache
import time

# Test connection pooling
conn1 = dashboard_conn_manager.get_connection()
conn2 = dashboard_conn_manager.get_connection()
assert conn1 is not conn2
dashboard_conn_manager.release_connection(conn1)
dashboard_conn_manager.release_connection(conn2)

# Test caching
cache = UnifiedCache(ttl_seconds=2)
cache.set('test_key', {'data': 'value'})
assert cache.get('test_key') == {'data': 'value'}
time.sleep(3)
assert cache.get('test_key') is None

print('✅ Service stability validation passed')
"
            """,
            "deliverables": [
                "dashboard/app/db/connection_manager.py",
                "dashboard/app/cache/unified_cache.py"
            ]
        },

        {
            "id": "gap-b4",
            "title": "Evidence Pack Pattern Miner",
            "priority": "medium",
            "estimated_hours": 1,
            "description": """
Build PatternMiner that extracts successful patterns from evidence_packs table.

Requirements:
1. Query evidence_packs with successful outcomes
2. Cluster similar approaches
3. Calculate success rates
4. Filter by minimum success rate (default 0.8)
5. Return actionable patterns with examples

Deliverable: dashboard/app/evidence/pattern_miner.py (100 lines)

Must include:
- extract_successful_patterns() method
- _cluster_similar_approaches() algorithm
- _calculate_success_rate() for patterns
- Integration with dashboard database
- Connection manager usage

See Z_AI_PHASE2_PLUS_GAPS.md Task B4 for detailed specifications.
            """,
            "validation": """
python3 -c "
from dashboard.app.evidence.pattern_miner import PatternMiner
miner = PatternMiner()
patterns = miner.extract_successful_patterns(min_success_rate=0.5)
assert isinstance(patterns, list)
if patterns:
    assert 'pattern_name' in patterns[0]
    assert 'success_rate' in patterns[0]
print('✅ PatternMiner validation passed')
"
            """,
            "deliverables": [
                "dashboard/app/evidence/pattern_miner.py"
            ]
        }
    ]

    return tasks


def main():
    """Delegate Phase 2 + Gaps to Z.AI."""
    import argparse

    parser = argparse.ArgumentParser(description="Delegate Phase 2 + Critical Gaps to Z.AI")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be delegated")
    parser.add_argument("--task-id", help="Delegate specific task only")

    args = parser.parse_args()

    # Create delegator
    delegator = ZAIDelegator()

    # Get tasks
    tasks = create_phase2_tasks()

    if args.task_id:
        # Filter to specific task
        tasks = [t for t in tasks if t["id"] == args.task_id]
        if not tasks:
            print(f"❌ Task {args.task_id} not found")
            return 1

    # Show summary
    print(f"\n🚀 Phase 2 + Critical Gaps Delegation Package")
    print(f"=" * 60)
    print(f"Total tasks: {len(tasks)}")
    print(f"Total effort: {sum(t['estimated_hours'] for t in tasks)} hours")
    print(f"Priority breakdown:")

    for priority in ['critical', 'high', 'medium']:
        count = len([t for t in tasks if t['priority'] == priority])
        if count > 0:
            print(f"  {priority.upper()}: {count} tasks")

    print(f"\n📋 Tasks to delegate:")
    for task in tasks:
        print(f"  [{task['id']}] {task['title']} ({task['estimated_hours']}h, {task['priority']})")

    if args.dry_run:
        print(f"\n✅ Dry run complete - no tasks delegated")
        return 0

    # Confirm delegation
    print(f"\n⚠️  This will start {len(tasks)} background tasks")
    response = input("Proceed with delegation? [y/N]: ")

    if response.lower() != 'y':
        print("❌ Delegation cancelled")
        return 0

    # Delegate all tasks
    print(f"\n📤 Delegating tasks...")
    results = []

    for task in tasks:
        print(f"\n  Delegating: {task['title']}")
        result = delegator.delegate_task(task)

        if result["status"] == "delegated":
            print(f"    ✅ Delegated to PID {result['pid']}")
            print(f"    📋 Log: {result['log_file']}")
            results.append(result)
        else:
            print(f"    ❌ Failed: {result.get('error', 'Unknown error')}")

    # Print summary
    print(f"\n" + "=" * 60)
    print(f"✅ Delegation complete!")
    print(f"   Total delegated: {len(results)}/{len(tasks)}")
    print(f"\n📊 Monitor progress:")
    print(f"   tail -f dashboard/logs/z_ai_*.log")

    print(f"\n🎯 Expected completion:")
    print(f"   Phase 2 tasks: 2-3 hours")
    print(f"   Gap closure tasks: 3-4 hours")
    print(f"   Total: 5-7 hours")

    print(f"\n💰 Token budget impact:")
    print(f"   Claude review: ~5K tokens")
    print(f"   Remaining: ~97K tokens (48.5%)")

    return 0


if __name__ == '__main__':
    sys.exit(main())


<!--AGTAG v1 START-->
{
  "version": "v1",
  "symbols": [
    {
      "name": "create_phase2_tasks",
      "kind": "function",
      "signature": "def create_phase2_tasks(...)",
      "lines": [
        22,
        375
      ],
      "summary_l0": "Function create_phase2_tasks",
      "contract_l1": "@io see source code"
    },
    {
      "name": "main",
      "kind": "function",
      "signature": "def main(...)",
      "lines": [
        378,
        460
      ],
      "summary_l0": "Function main",
      "contract_l1": "@io see source code"
    }
  ]
}
<!--AGTAG v1 END-->
