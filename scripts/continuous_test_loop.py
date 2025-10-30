#!/usr/bin/env python3

Continuous context quality testing loop.

This script runs continuously during development to validate that
assembled context produces same quality answers as full context.

Perfect for:
1. Testing while Backend builds extended schema
2. Validating context assembly improvements
3. Catching quality degradation early
4. Measuring real token savings

Usage:
  python scripts/continuous_test_loop.py

  # Or run specific test cases
  python scripts/continuous_test_loop.py --test-case session_startup


import os
import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from agentdb.glm_generator import GLMGenerator


# Test cases: Different query types to validate
TEST_CASES = [
    {
        'id': 'session_startup',
        'query': 'What should I work on next?',
        'assembled_context': '''
## AGENT CONTEXT
Agent: backend
Role: developer
Capabilities: [database, schema_design, api_development]
Current Mission: Extended schema implementation (Task 1: Migration 003)

## PROJECT CONTEXT
Project: agentdb-mvp
Phase: Architecture pivot (Option B - Perfect Prompt Builder)
Progress: 68% complete (13.5h/20h)
Tests: 10/10 passing

## PENDING WORK
1. Migration 003 (agents, env, tools tables) - 2-3h - IN PROGRESS
2. AgentManager class - 1.5h - PENDING
3. EnvironmentTracker class - 1h - PENDING
''',
        'expected_quality': 0.90
    },
    {
        'id': 'code_understanding',
        'query': 'How does the agent registration work?',
        'assembled_context': '''
## RELEVANT CODE
src/agentdb/agent_manager.py::register_agent
L0: Registers new agent with capabilities and mission tracking
L1: @io (agent_id: str, role: str, capabilities: List[str]) -> Dict[str, Any]. Inserts agent into database.
L2:
1. Validate input parameters
2. Convert capabilities list to JSON
3. Execute INSERT INTO agents table
4. Commit transaction
5. Return agent definition via get_agent()
''',
        'expected_quality': 0.85
    },
    {
        'id': 'architecture_question',
        'query': 'Why did we pivot from documentation-only to full context system?',
        'assembled_context': '''
## ARCHITECTURE DECISION
Decision: Pivot to Option B (Full Perfect Prompt Builder)
Reason: User confirmed need for complete context (code + agent + env + tools), not just docs

## CURRENT STATE
- Coverage: 2% (15 markdown files only)
- No Python code indexed
- No agent/env/tool context

## TARGET STATE
- Coverage: 100% (all project files + metadata)
- Full Python code indexed with L0/L1/L2
- Agent definitions, environment state, tool registry in DB
- Multi-source context assembly

## IMPACT
Token savings: 96% (200 tokens vs 5000 tokens) with BETTER quality
''',
        'expected_quality': 0.90
    },
    {
        'id': 'implementation_details',
        'query': 'Show me how to create the agents table migration',
        'assembled_context': '''
## TASK DETAILS
Task 1: Migration 003 - Extended Schema
File: src/agentdb/migrations/003_extended_schema.py

## TABLE SCHEMA (L2)
agents table:
1. Create table with columns: agent_id (PK), role, capabilities (JSON), status, current_mission
2. Add foreign key to missions table
3. Create indexes on status and role
4. Insert default tools (agentdb_focus, agentdb_zoom, etc.)
5. Create agent_current_state view (joins agents + missions + tools)
''',
        'expected_quality': 0.80  # Lower expectation - might need L4 for exact code
    }
]


def load_full_context_simulation(test_case_id: str) -> str:
    """Simulate loading full files for a test case.

    In reality, this would load actual files. For testing,
    we simulate by expanding the assembled context.
    """

    # Simulate full context (10x larger than assembled)
    base_contexts = {
        'session_startup': '''
[Full MISSION_BACKEND_EXTENDED_SCHEMA.md - 500 lines]
[Full PARALLEL_EXECUTION_STATUS.md - 400 lines]
[Full ARCHITECTURE_PIVOT_SUMMARY.md - 300 lines]
[Full .claude/profiles/PROFILE_BACKEND.md - 200 lines]
Total: ~5000 tokens
''',
        'code_understanding': '''
[Full src/agentdb/agent_manager.py - 300 lines]
[Full src/agentdb/core.py - 1200 lines]
Total: ~3000 tokens
''',
        'architecture_question': '''
[Full ARCHITECTURE_GAP_ANALYSIS.md - 600 lines]
[Full ARCHITECTURE_PIVOT_SUMMARY.md - 500 lines]
[Full VALIDATION_INTEGRATION_ANALYSIS.md - 400 lines]
Total: ~3500 tokens
''',
        'implementation_details': '''
[Full migration 001_initial_schema.py - 100 lines]
[Full migration 002_add_db_version.py - 50 lines]
[Full src/agentdb/migrations/__init__.py - 189 lines]
[Full MISSION_BACKEND_EXTENDED_SCHEMA.md with complete code examples - 500 lines]
Total: ~2000 tokens
'''
    }

    return base_contexts.get(test_case_id, '[Full project context...]')


def run_test_case(
    test_case: Dict[str, Any],
    glm: GLMGenerator
) -> Dict[str, Any]:
    """Run a single test case and return results.

    Args:
        test_case: Test case definition
        glm: GLM generator instance

    Returns:
        Dict with test results and metrics
    """

    print(f"\n{'='*60}")
    print(f"TEST: {test_case['id']}")
    print(f"QUERY: {test_case['query']}")
    print('='*60)

    assembled = test_case['assembled_context']
    full = load_full_context_simulation(test_case['id'])

    print(f"\nContext sizes:")
    print(f"  Assembled: ~{len(assembled.split())} words")
    print(f"  Full: ~{len(full.split())} words")

    # Validate context quality
    result = glm.validate_context_quality(
        query=test_case['query'],
        assembled_context=assembled,
        full_context=full
    )

    # Check if meets expected quality
    expected = test_case['expected_quality']
    actual = result['similarity_score']
    passed = actual >= expected

    result['test_id'] = test_case['id']
    result['expected_quality'] = expected
    result['passed'] = passed
    result['timestamp'] = datetime.now().isoformat()

    # Print results
    print(f"\n{'✅ PASS' if passed else '❌ FAIL'}")
    print(f"Similarity: {actual:.2%} (expected: {expected:.2%})")
    print(f"Token savings: {result['token_savings']}")

    if not passed:
        print(f"\n⚠️ Quality below threshold!")
        print(f"Reasoning: {result.get('reasoning', 'N/A')}")
        if result.get('key_differences'):
            print("Key differences:")
            for diff in result['key_differences']:
                print(f"  - {diff}")

    return result


def run_continuous_loop(
    interval_seconds: int = 300,  # 5 minutes
    test_case_ids: List[str] = None
):
    """Run continuous testing loop.

    Args:
        interval_seconds: Seconds between test runs
        test_case_ids: Specific test cases to run (or None for all)
    """

    glm = GLMGenerator()

    # Filter test cases
    if test_case_ids:
        test_cases = [tc for tc in TEST_CASES if tc['id'] in test_case_ids]
    else:
        test_cases = TEST_CASES

    print("\n" + "="*60)
    print("CONTINUOUS CONTEXT QUALITY TESTING")
    print("="*60)
    print(f"Test cases: {len(test_cases)}")
    print(f"Interval: {interval_seconds}s")
    print(f"Press Ctrl+C to stop")
    print("="*60)

    run_count = 0
    results_history = []

    try:
        while True:
            run_count += 1
            print(f"\n\n{'#'*60}")
            print(f"RUN #{run_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print('#'*60)

            run_results = []

            for test_case in test_cases:
                try:
                    result = run_test_case(test_case, glm)
                    run_results.append(result)
                    time.sleep(2)  # Brief pause between tests

                except Exception as e:
                    print(f"\n❌ Test failed with error: {e}")
                    run_results.append({
                        'test_id': test_case['id'],
                        'error': str(e),
                        'passed': False
                    })

            results_history.append({
                'run': run_count,
                'timestamp': datetime.now().isoformat(),
                'results': run_results
            })

            # Print summary
            print(f"\n{'='*60}")
            print(f"RUN #{run_count} SUMMARY")
            print('='*60)

            passed = sum(1 for r in run_results if r.get('passed', False))
            total = len(run_results)
            avg_similarity = sum(r.get('similarity_score', 0) for r in run_results) / total if total > 0 else 0

            print(f"Pass rate: {passed}/{total} ({passed/total*100:.1f}%)")
            print(f"Avg similarity: {avg_similarity:.2%}")

            # Save results
            results_file = Path('test_results_continuous.json')
            with open(results_file, 'w') as f:
                json.dump(results_history, f, indent=2)

            print(f"\nResults saved to: {results_file}")

            # Wait for next run
            print(f"\nNext run in {interval_seconds}s...")
            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\n\n✋ Stopped by user")
        print(f"\nTotal runs: {run_count}")
        print(f"Results saved to: test_results_continuous.json")


def run_single_pass(test_case_ids: List[str] = None):
    """Run tests once (not continuous).

    Args:
        test_case_ids: Specific test cases to run (or None for all)
    """

    glm = GLMGenerator()

    # Filter test cases
    if test_case_ids:
        test_cases = [tc for tc in TEST_CASES if tc['id'] in test_case_ids]
    else:
        test_cases = TEST_CASES

    print("\n" + "="*60)
    print("CONTEXT QUALITY TEST (Single Pass)")
    print("="*60)

    results = []

    for test_case in test_cases:
        try:
            result = run_test_case(test_case, glm)
            results.append(result)
            time.sleep(2)
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            results.append({
                'test_id': test_case['id'],
                'error': str(e),
                'passed': False
            })

    # Final summary
    print(f"\n\n{'='*60}")
    print("FINAL SUMMARY")
    print('='*60)

    passed = sum(1 for r in results if r.get('passed', False))
    total = len(results)
    avg_similarity = sum(r.get('similarity_score', 0) for r in results) / total if total > 0 else 0

    print(f"Pass rate: {passed}/{total} ({passed/total*100:.1f}%)")
    print(f"Avg similarity: {avg_similarity:.2%}")

    print("\nIndividual results:")
    for r in results:
        status = '✅' if r.get('passed') else '❌'
        score = r.get('similarity_score', 0)
        print(f"  {status} {r['test_id']}: {score:.2%}")

    return results


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Continuous context quality testing')
    parser.add_argument('--continuous', action='store_true',
                       help='Run continuously (default: single pass)')
    parser.add_argument('--interval', type=int, default=300,
                       help='Seconds between runs in continuous mode')
    parser.add_argument('--test-case', action='append',
                       help='Specific test case(s) to run')

    args = parser.parse_args()

    # Check for API key
    if not os.getenv('Z_AI_API_KEY'):
        print("❌ Z_AI_API_KEY environment variable not set")
        print("\nSet it with:")
        print("  export Z_AI_API_KEY='your_key_here'")
        exit(1)

    if args.continuous:
        run_continuous_loop(
            interval_seconds=args.interval,
            test_case_ids=args.test_case
        )
    else:
        run_single_pass(test_case_ids=args.test_case)


<!--AGTAG v1 START-->
{
  "version": "v1",
  "symbols": [
    {
      "name": "load_full_context_simulation",
      "kind": "function",
      "signature": "def load_full_context_simulation(...)",
      "lines": [
        121,
        157
      ],
      "summary_l0": "Function load_full_context_simulation",
      "contract_l1": "@io see source code"
    },
    {
      "name": "run_test_case",
      "kind": "function",
      "signature": "def run_test_case(...)",
      "lines": [
        160,
        216
      ],
      "summary_l0": "Function run_test_case",
      "contract_l1": "@io see source code"
    },
    {
      "name": "run_continuous_loop",
      "kind": "function",
      "signature": "def run_continuous_loop(...)",
      "lines": [
        219,
        304
      ],
      "summary_l0": "Function run_continuous_loop",
      "contract_l1": "@io see source code"
    },
    {
      "name": "run_single_pass",
      "kind": "function",
      "signature": "def run_single_pass(...)",
      "lines": [
        307,
        359
      ],
      "summary_l0": "Function run_single_pass",
      "contract_l1": "@io see source code"
    }
  ]
}
<!--AGTAG v1 END-->
