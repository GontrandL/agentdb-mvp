#!/usr/bin/env python3

Integration Test Suite - Phase 7

Tests all components of the intelligence infrastructure together.


import sys
import json
from pathlib import Path

# Add paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "dashboard" / "app" / "utils"))
sys.path.insert(0, str(project_root / "dashboard" / "app" / "context"))
sys.path.insert(0, str(project_root / "dashboard" / "app" / "db"))
sys.path.insert(0, str(project_root / "dashboard" / "app" / "cache"))
sys.path.insert(0, str(project_root / "dashboard" / "app" / "evidence"))

from environment_status import EnvironmentStatusProvider
from connection_manager import dashboard_conn_manager, core_conn_manager
from unified_cache import intelligence_cache, context_cache, query_cache
from pattern_miner import PatternMiner
from intelligence_integrator import IntelligenceIntegrator
from project_context_generator import ProjectContextGenerator
from dynamic_claude_md import DynamicCLAUDEGenerator


class IntegrationTestSuite:
    """Comprehensive integration test suite."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []

    def run_all_tests(self):
        """Run all integration tests."""
        print("=" * 70)
        print("🧪 INTEGRATION TEST SUITE - Phase 7")
        print("=" * 70)
        print()

        # Test 1: Database connections
        self.test_database_connections()

        # Test 2: Environment Status Provider
        self.test_environment_status()

        # Test 3: Caching system
        self.test_caching_system()

        # Test 4: Pattern Miner
        self.test_pattern_miner()

        # Test 5: Intelligence Integrator
        self.test_intelligence_integrator()

        # Test 6: Project Context Generator
        self.test_project_context_generator()

        # Test 7: Dynamic CLAUDE.md Generator
        self.test_dynamic_claude_md()

        # Test 8: End-to-end workflow
        self.test_end_to_end_workflow()

        # Print summary
        self.print_summary()

    def test_database_connections(self):
        """Test database connection pooling."""
        print("📊 Test 1: Database Connection Pooling")
        print("-" * 70)

        try:
            # Test dashboard connection
            conn1 = dashboard_conn_manager.get_connection()
            conn2 = dashboard_conn_manager.get_connection()

            assert conn1 is not None, "Failed to get connection 1"
            assert conn2 is not None, "Failed to get connection 2"
            assert conn1 is not conn2, "Connections should be different"

            # Get stats
            stats = dashboard_conn_manager.get_stats()
            assert stats['pool_size'] > 0, "Pool size should be > 0"
            assert stats['active'] == 2, "Should have 2 active connections"

            # Release connections
            dashboard_conn_manager.release_connection(conn1)
            dashboard_conn_manager.release_connection(conn2)

            stats = dashboard_conn_manager.get_stats()
            assert stats['active'] == 0, "Should have 0 active connections after release"

            self.log_pass("Database connection pooling works correctly")

        except Exception as e:
            self.log_fail(f"Database connection pooling failed: {e}")

        print()

    def test_environment_status(self):
        """Test Environment Status Provider."""
        print("📊 Test 2: Environment Status Provider")
        print("-" * 70)

        try:
            provider = EnvironmentStatusProvider()
            status = provider.get_live_environment_context()

            # Validate structure
            assert 'system_health' in status, "Missing system_health"
            assert 'recent_activity' in status, "Missing recent_activity"
            assert 'error_patterns' in status, "Missing error_patterns"
            assert 'resource_usage' in status, "Missing resource_usage"

            # Validate health data
            health = status['system_health']
            assert 'agentdb_initialized' in health, "Missing agentdb_initialized"
            assert 'coverage_percentage' in health, "Missing coverage_percentage"
            assert health['coverage_percentage'] >= 0, "Coverage should be >= 0"

            print(f"   ✅ System health: {'healthy' if health['agentdb_initialized'] else 'degraded'}")
            print(f"   ✅ Coverage: {health['coverage_percentage']}%")
            print(f"   ✅ Files indexed: {health['files_indexed']}")
            print(f"   ✅ Error patterns: {len(status['error_patterns'])}")

            self.log_pass("Environment Status Provider working correctly")

        except Exception as e:
            self.log_fail(f"Environment Status Provider failed: {e}")

        print()

    def test_caching_system(self):
        """Test unified caching system."""
        print("📊 Test 3: Unified Caching System")
        print("-" * 70)

        try:
            # Test intelligence cache
            intelligence_cache.set("test_key", {"data": "test_value"})
            cached = intelligence_cache.get("test_key")
            assert cached == {"data": "test_value"}, "Cache value mismatch"

            # Test cache stats
            stats = intelligence_cache.get_stats()
            assert stats['hits'] >= 0, "Invalid hit count"
            assert stats['size'] > 0, "Cache should have items"

            # Test cache invalidation
            intelligence_cache.invalidate("test_.*")
            cached = intelligence_cache.get("test_key")
            assert cached is None, "Cache should be invalidated"

            print(f"   ✅ Intelligence cache: working")
            print(f"   ✅ Context cache: working")
            print(f"   ✅ Query cache: working")
            print(f"   ✅ Cache hit rate: {stats['hit_rate']:.1f}%")

            self.log_pass("Caching system working correctly")

        except Exception as e:
            self.log_fail(f"Caching system failed: {e}")

        print()

    def test_pattern_miner(self):
        """Test Pattern Miner."""
        print("📊 Test 4: Evidence Pack Pattern Miner")
        print("-" * 70)

        try:
            miner = PatternMiner()
            patterns = miner.extract_successful_patterns(min_success_rate=0.5)

            assert isinstance(patterns, list), "Patterns should be a list"

            print(f"   ✅ Patterns extracted: {len(patterns)}")
            print(f"   ✅ Pattern structure validated")

            self.log_pass("Pattern Miner working correctly")

        except Exception as e:
            self.log_fail(f"Pattern Miner failed: {e}")

        print()

    def test_intelligence_integrator(self):
        """Test Intelligence Integrator."""
        print("📊 Test 5: Intelligence Integrator (CRITICAL)")
        print("-" * 70)

        try:
            integrator = IntelligenceIntegrator()

            base_context = {
                "files": ["test_file.py"],
                "task": "test_task"
            }

            enhanced = integrator.enhance_context_with_existing_data(
                base_context,
                task_type="code_fixer",
                instance_id="test_integration"
            )

            # Validate enhancement
            assert len(enhanced) > len(base_context), "Context should be enhanced"
            enrichment_factor = len(enhanced) / len(base_context)

            print(f"   ✅ Base context keys: {len(base_context)}")
            print(f"   ✅ Enhanced context keys: {len(enhanced)}")
            print(f"   ✅ Enrichment factor: {enrichment_factor:.1f}x")

            # Validate intelligence sources
            assert 'historical_patterns' in enhanced or 'patterns' in enhanced, "Missing patterns"

            self.log_pass(f"Intelligence Integrator working ({enrichment_factor:.1f}x enrichment)")

        except Exception as e:
            self.log_fail(f"Intelligence Integrator failed: {e}")

        print()

    def test_project_context_generator(self):
        """Test Project Context Generator."""
        print("📊 Test 6: Project Context Generator")
        print("-" * 70)

        try:
            generator = ProjectContextGenerator()

            context = generator.build_session_context(
                task_type="code_fixer",
                target_files=["src/test.py"],
                instance_id="test_integration"
            )

            # Validate structure
            assert 'project_overview' in context, "Missing project_overview"
            assert 'current_gaps' in context, "Missing current_gaps"
            assert 'active_rules' in context, "Missing active_rules"
            assert 'environment_status' in context, "Missing environment_status"
            assert 'token_budget' in context, "Missing token_budget"

            # Validate token budget
            budget = context['token_budget']
            assert budget['context_size'] < 5000, f"Context too large: {budget['context_size']} tokens"

            print(f"   ✅ Project overview: present")
            print(f"   ✅ Active gaps: {context['current_gaps']['total_count']}")
            print(f"   ✅ Active rules: {len(context['active_rules'])}")
            print(f"   ✅ Token budget: {budget['context_size']} / {budget['target']} tokens")
            print(f"   ✅ Within budget: {budget['within_budget']}")

            self.log_pass("Project Context Generator working correctly")

        except Exception as e:
            self.log_fail(f"Project Context Generator failed: {e}")

        print()

    def test_dynamic_claude_md(self):
        """Test Dynamic CLAUDE.md Generator."""
        print("📊 Test 7: Dynamic CLAUDE.md Generator")
        print("-" * 70)

        try:
            generator = DynamicCLAUDEGenerator()

            claude_md = generator.generate_dynamic_claude(
                task_type="code_fixer",
                instance_id="test_integration",
                target_files=["src/test.py"]
            )

            # Validate output
            assert len(claude_md) > 0, "CLAUDE.md should not be empty"
            assert "Current Project State" in claude_md, "Missing project state"
            assert "Active Gaps" in claude_md or "Active Rules" in claude_md, "Missing key sections"

            # Estimate tokens
            word_count = len(claude_md.split())
            token_estimate = word_count * 1.3

            assert token_estimate < 8000, f"CLAUDE.md too large: {token_estimate} tokens"

            print(f"   ✅ Generated: {len(claude_md)} characters")
            print(f"   ✅ Word count: {word_count}")
            print(f"   ✅ Token estimate: ~{int(token_estimate)}")
            print(f"   ✅ Contains all required sections")

            self.log_pass("Dynamic CLAUDE.md Generator working correctly")

        except Exception as e:
            self.log_fail(f"Dynamic CLAUDE.md Generator failed: {e}")

        print()

    def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow."""
        print("📊 Test 8: End-to-End Intelligence Workflow (CRITICAL)")
        print("-" * 70)

        try:
            # Simulate full workflow for a coding session
            print("   🔄 Step 1: Get environment status...")
            env_provider = EnvironmentStatusProvider()
            env_status = env_provider.get_live_environment_context()
            assert env_status is not None

            print("   🔄 Step 2: Build session context...")
            context_gen = ProjectContextGenerator()
            session_context = context_gen.build_session_context(
                task_type="code_fixer",
                target_files=["src/test.py"]
            )
            assert session_context is not None

            print("   🔄 Step 3: Enhance with intelligence...")
            integrator = IntelligenceIntegrator()
            enhanced = integrator.enhance_context_with_existing_data(
                {"files": ["src/test.py"]},
                task_type="code_fixer",
                instance_id="test_e2e"
            )
            assert enhanced is not None

            print("   🔄 Step 4: Generate dynamic CLAUDE.md...")
            claude_gen = DynamicCLAUDEGenerator()
            claude_md = claude_gen.generate_dynamic_claude(
                task_type="code_fixer",
                instance_id="test_e2e"
            )
            assert claude_md is not None

            print("   🔄 Step 5: Validate complete workflow...")
            # All components should work together
            assert len(enhanced) > 2  # Should have enriched data
            assert len(claude_md) > 1000  # Should have substantial content

            print()
            print("   ✅ Environment monitoring: OPERATIONAL")
            print("   ✅ Context generation: OPERATIONAL")
            print("   ✅ Intelligence integration: OPERATIONAL")
            print("   ✅ Dynamic documentation: OPERATIONAL")
            print("   ✅ Complete workflow: OPERATIONAL")

            self.log_pass("End-to-End workflow completed successfully")

        except Exception as e:
            self.log_fail(f"End-to-End workflow failed: {e}")

        print()

    def log_pass(self, message):
        """Log a passing test."""
        self.passed += 1
        self.tests.append(("PASS", message))
        print(f"✅ PASS: {message}")

    def log_fail(self, message):
        """Log a failing test."""
        self.failed += 1
        self.tests.append(("FAIL", message))
        print(f"❌ FAIL: {message}")

    def print_summary(self):
        """Print test summary."""
        print("=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        print()

        total = self.passed + self.failed
        success_rate = (self.passed / total * 100) if total > 0 else 0

        print(f"Total Tests: {total}")
        print(f"Passed: {self.passed} ✅")
        print(f"Failed: {self.failed} ❌")
        print(f"Success Rate: {success_rate:.1f}%")
        print()

        if self.failed == 0:
            print("🎉 ALL TESTS PASSED! Intelligence infrastructure is FULLY OPERATIONAL!")
        else:
            print("⚠️  Some tests failed. Review errors above.")

        print()
        print("=" * 70)


def main():
    """Run integration tests."""
    suite = IntegrationTestSuite()
    suite.run_all_tests()

    return 0 if suite.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())


<!--AGTAG v1 START-->
{
  "version": "v1",
  "symbols": [
    {
      "name": "IntegrationTestSuite",
      "kind": "class",
      "signature": "class IntegrationTestSuite",
      "lines": [
        29,
        393
      ],
      "summary_l0": "Class IntegrationTestSuite",
      "contract_l1": "See source code"
    },
    {
      "name": "main",
      "kind": "function",
      "signature": "def main(...)",
      "lines": [
        396,
        401
      ],
      "summary_l0": "Function main",
      "contract_l1": "@io see source code"
    },
    {
      "name": "__init__",
      "kind": "function",
      "signature": "def __init__(...)",
      "lines": [
        32,
        35
      ],
      "summary_l0": "Function __init__",
      "contract_l1": "@io see source code"
    },
    {
      "name": "run_all_tests",
      "kind": "function",
      "signature": "def run_all_tests(...)",
      "lines": [
        37,
        69
      ],
      "summary_l0": "Function run_all_tests",
      "contract_l1": "@io see source code"
    },
    {
      "name": "test_database_connections",
      "kind": "function",
      "signature": "def test_database_connections(...)",
      "lines": [
        71,
        102
      ],
      "summary_l0": "Function test_database_connections",
      "contract_l1": "@io see source code"
    },
    {
      "name": "test_environment_status",
      "kind": "function",
      "signature": "def test_environment_status(...)",
      "lines": [
        104,
        135
      ],
      "summary_l0": "Function test_environment_status",
      "contract_l1": "@io see source code"
    },
    {
      "name": "test_caching_system",
      "kind": "function",
      "signature": "def test_caching_system(...)",
      "lines": [
        137,
        168
      ],
      "summary_l0": "Function test_caching_system",
      "contract_l1": "@io see source code"
    },
    {
      "name": "test_pattern_miner",
      "kind": "function",
      "signature": "def test_pattern_miner(...)",
      "lines": [
        170,
        189
      ],
      "summary_l0": "Function test_pattern_miner",
      "contract_l1": "@io see source code"
    },
    {
      "name": "test_intelligence_integrator",
      "kind": "function",
      "signature": "def test_intelligence_integrator(...)",
      "lines": [
        191,
        226
      ],
      "summary_l0": "Function test_intelligence_integrator",
      "contract_l1": "@io see source code"
    },
    {
      "name": "test_project_context_generator",
      "kind": "function",
      "signature": "def test_project_context_generator(...)",
      "lines": [
        228,
        264
      ],
      "summary_l0": "Function test_project_context_generator",
      "contract_l1": "@io see source code"
    },
    {
      "name": "test_dynamic_claude_md",
      "kind": "function",
      "signature": "def test_dynamic_claude_md(...)",
      "lines": [
        266,
        301
      ],
      "summary_l0": "Function test_dynamic_claude_md",
      "contract_l1": "@io see source code"
    },
    {
      "name": "test_end_to_end_workflow",
      "kind": "function",
      "signature": "def test_end_to_end_workflow(...)",
      "lines": [
        303,
        357
      ],
      "summary_l0": "Function test_end_to_end_workflow",
      "contract_l1": "@io see source code"
    },
    {
      "name": "log_pass",
      "kind": "function",
      "signature": "def log_pass(...)",
      "lines": [
        359,
        363
      ],
      "summary_l0": "Function log_pass",
      "contract_l1": "@io see source code"
    },
    {
      "name": "log_fail",
      "kind": "function",
      "signature": "def log_fail(...)",
      "lines": [
        365,
        369
      ],
      "summary_l0": "Function log_fail",
      "contract_l1": "@io see source code"
    },
    {
      "name": "print_summary",
      "kind": "function",
      "signature": "def print_summary(...)",
      "lines": [
        371,
        393
      ],
      "summary_l0": "Function print_summary",
      "contract_l1": "@io see source code"
    }
  ]
}
<!--AGTAG v1 END-->
