#!/usr/bin/env python3

Test Auto-Collection Integration

Validates that automatic intelligence collection works end-to-end:
1. File access triggers session_messages entry
2. Trace events created automatically
3. Embedding jobs queued
4. Evidence packs created on success


import sys
import time
from pathlib import Path

# Add paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "dashboard" / "app"))
sys.path.insert(0, str(project_root / "dashboard"))

from app.db.connection_manager import dashboard_conn_manager
from sqlalchemy import text


class AutoCollectionTestSuite:
    """Test automatic intelligence collection."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []

    def run_all_tests(self):
        """Run all auto-collection tests."""
        print("=" * 70)
        print("🧪 AUTO-COLLECTION INTEGRATION TEST")
        print("=" * 70)
        print()

        # Test 1: Baseline counts
        self.test_baseline_counts()

        # Test 2: Import auto_collector module
        self.test_import_auto_collector()

        # Test 3: Test log_context_operation
        self.test_log_context_operation()

        # Test 4: Test create_trace_for_operation
        self.test_create_trace()

        # Test 5: Test queue_embedding
        self.test_queue_embedding()

        # Test 6: Test create_evidence_pack
        self.test_create_evidence_pack()

        # Test 7: Verify all 6 intelligence sources have data
        self.test_verify_all_sources()

        # Print summary
        self.print_summary()

    def test_baseline_counts(self):
        """Get baseline counts for all intelligence sources."""
        print("📊 Test 1: Baseline Intelligence Source Counts")
        print("-" * 70)

        try:
            conn = dashboard_conn_manager.get_connection()
            cursor = conn.cursor()

            sources = [
                'session_messages',
                'trace_events',
                'evidence_packs',
                'tool_violations',
                'architectural_patterns',
                'autonomous_gaps'
            ]

            self.baseline = {}
            for source in sources:
                cursor.execute(f"SELECT COUNT(*) FROM {source}")
                count = cursor.fetchone()[0]
                self.baseline[source] = count
                print(f"   {source}: {count} rows")

            dashboard_conn_manager.release_connection(conn)

            self.log_pass("Baseline counts retrieved")

        except Exception as e:
            self.log_fail(f"Baseline count failed: {e}")

        print()

    def test_import_auto_collector(self):
        """Test that auto_collector module can be imported."""
        print("📊 Test 2: Import auto_collector Module")
        print("-" * 70)

        try:
            from app.intelligence.auto_collector import (
                log_context_operation,
                create_trace_for_operation,
                add_trace_event,
                complete_trace,
                queue_embedding,
                create_evidence_pack,
                auto_create_evidence_pack_on_success,
                get_collection_stats
            )

            print("   ✅ All functions imported successfully")
            self.auto_collector = sys.modules['app.intelligence.auto_collector']
            self.log_pass("auto_collector module imported")

        except Exception as e:
            self.log_fail(f"Import failed: {e}")

        print()

    def test_log_context_operation(self):
        """Test logging context operation to session_messages."""
        print("📊 Test 3: Log Context Operation (session_messages)")
        print("-" * 70)

        try:
            import sys
            import importlib.util

            # Load db module directly from file
            spec = importlib.util.spec_from_file_location("db", project_root / "dashboard" / "app" / "db.py")
            db_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(db_module)

            from app.intelligence.auto_collector import log_context_operation

            db = db_module.SessionLocal()

            msg_id = log_context_operation(
                db,
                project_id="test_project",
                instance_id="test_instance",
                operation="test_operation",
                details={"test": "data"},
                severity="info"
            )

            assert msg_id != "", "Message ID should not be empty"

            # Verify it was written
            result = db.execute(text("SELECT COUNT(*) FROM session_messages WHERE id = :id"), {"id": msg_id})
            count = result.fetchone()[0]
            assert count == 1, "Should have 1 message"

            print(f"   ✅ Created message: {msg_id}")
            self.log_pass("session_messages logging works")

        except Exception as e:
            self.log_fail(f"session_messages logging failed: {e}")

        print()

    def test_create_trace(self):
        """Test creating trace and adding events."""
        print("📊 Test 4: Create Trace (traces + trace_events)")
        print("-" * 70)

        try:
            import importlib.util

            # Load db module directly from file
            spec = importlib.util.spec_from_file_location("db", project_root / "dashboard" / "app" / "db.py")
            db_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(db_module)

            from app.intelligence.auto_collector import (
                create_trace_for_operation,
                add_trace_event,
                complete_trace
            )

            db = db_module.SessionLocal()

            # Create trace
            trace_id = create_trace_for_operation(
                db,
                session_id="test_session",
                operation="test_trace",
                metadata={"test": "data"}
            )

            assert trace_id != "", "Trace ID should not be empty"
            print(f"   ✅ Created trace: {trace_id}")

            # Add event
            success = add_trace_event(
                db,
                trace_id=trace_id,
                event_type="test_event",
                event_data={"event": "data"},
                duration_ms=100,
                success=True
            )

            assert success, "Event should be added successfully"
            print(f"   ✅ Added event to trace")

            # Complete trace
            success = complete_trace(db, trace_id, tokens_used=500)
            assert success, "Trace should be completed"
            print(f"   ✅ Completed trace")

            # Verify trace_events table has data
            result = db.execute(text("SELECT COUNT(*) FROM trace_events WHERE trace_id = :id"), {"id": trace_id})
            count = result.fetchone()[0]
            assert count == 1, "Should have 1 trace event"

            self.log_pass("Trace recording works")

        except Exception as e:
            self.log_fail(f"Trace recording failed: {e}")

        print()

    def test_queue_embedding(self):
        """Test queuing embeddings."""
        print("📊 Test 5: Queue Embedding (embedding_jobs)")
        print("-" * 70)

        try:
            import importlib.util

            # Load db module directly from file
            spec = importlib.util.spec_from_file_location("db", project_root / "dashboard" / "app" / "db.py")
            db_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(db_module)

            from app.intelligence.auto_collector import queue_embedding

            db = db_module.SessionLocal()

            success = queue_embedding(
                db,
                item_id="test_item_123",
                item_type="code",
                text="def test(): pass",
                metadata={"file": "test.py"}
            )

            assert success, "Embedding should be queued"

            # Verify it was written
            result = db.execute(text("SELECT COUNT(*) FROM embedding_jobs WHERE item_id = :id"), {"id": "test_item_123"})
            count = result.fetchone()[0]
            assert count == 1, "Should have 1 embedding job"

            print(f"   ✅ Queued embedding for test_item_123")
            self.log_pass("Embedding queue works")

        except Exception as e:
            self.log_fail(f"Embedding queue failed: {e}")

        print()

    def test_create_evidence_pack(self):
        """Test creating evidence packs."""
        print("📊 Test 6: Create Evidence Pack")
        print("-" * 70)

        try:
            import importlib.util

            # Load db module directly from file
            spec = importlib.util.spec_from_file_location("db", project_root / "dashboard" / "app" / "db.py")
            db_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(db_module)

            from app.intelligence.auto_collector import (
                create_trace_for_operation,
                create_evidence_pack
            )

            db = db_module.SessionLocal()

            # Create trace first (evidence packs need trace_id)
            trace_id = create_trace_for_operation(
                db,
                session_id="test_session_ep",
                operation="test_evidence"
            )

            # Create evidence pack
            pack_id = create_evidence_pack(
                db,
                trace_id=trace_id,
                reasoning="Test evidence pack creation",
                symbols_changed=[{"file": "test.py", "symbol": "test_func"}],
                outcome="success",
                metadata={"test": "data"}
            )

            assert pack_id != "", "Evidence pack ID should not be empty"

            # Verify it was written
            result = db.execute(text("SELECT COUNT(*) FROM evidence_packs WHERE id = :id"), {"id": pack_id})
            count = result.fetchone()[0]
            assert count == 1, "Should have 1 evidence pack"

            print(f"   ✅ Created evidence pack: {pack_id}")
            self.log_pass("Evidence pack creation works")

        except Exception as e:
            self.log_fail(f"Evidence pack creation failed: {e}")

        print()

    def test_verify_all_sources(self):
        """Verify all 6 intelligence sources now have data."""
        print("📊 Test 7: Verify All Intelligence Sources Have Data")
        print("-" * 70)

        try:
            conn = dashboard_conn_manager.get_connection()
            cursor = conn.cursor()

            sources = [
                'session_messages',
                'trace_events',
                'evidence_packs',
                'tool_violations',
                'architectural_patterns',
                'autonomous_gaps'
            ]

            all_populated = True
            for source in sources:
                cursor.execute(f"SELECT COUNT(*) FROM {source}")
                count = cursor.fetchone()[0]
                baseline = self.baseline.get(source, 0)
                delta = count - baseline

                if count > 0:
                    print(f"   ✅ {source}: {count} rows (Δ{delta:+d})")
                else:
                    print(f"   ⚠️  {source}: {count} rows (EMPTY)")
                    all_populated = False

            dashboard_conn_manager.release_connection(conn)

            if all_populated:
                self.log_pass("All 6 intelligence sources populated")
            else:
                self.log_fail("Some intelligence sources still empty")

        except Exception as e:
            self.log_fail(f"Verification failed: {e}")

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
            print("🎉 ALL TESTS PASSED! Auto-collection is FULLY OPERATIONAL!")
        else:
            print("⚠️  Some tests failed. Review errors above.")

        print()
        print("=" * 70)


def main():
    """Run auto-collection tests."""
    suite = AutoCollectionTestSuite()
    suite.run_all_tests()

    return 0 if suite.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())


<!--AGTAG v1 START-->
{
  "version": "v1",
  "symbols": [
    {
      "name": "AutoCollectionTestSuite",
      "kind": "class",
      "signature": "class AutoCollectionTestSuite",
      "lines": [
        25,
        397
      ],
      "summary_l0": "Class AutoCollectionTestSuite",
      "contract_l1": "See source code"
    },
    {
      "name": "main",
      "kind": "function",
      "signature": "def main(...)",
      "lines": [
        400,
        405
      ],
      "summary_l0": "Function main",
      "contract_l1": "@io see source code"
    },
    {
      "name": "__init__",
      "kind": "function",
      "signature": "def __init__(...)",
      "lines": [
        28,
        31
      ],
      "summary_l0": "Function __init__",
      "contract_l1": "@io see source code"
    },
    {
      "name": "run_all_tests",
      "kind": "function",
      "signature": "def run_all_tests(...)",
      "lines": [
        33,
        62
      ],
      "summary_l0": "Function run_all_tests",
      "contract_l1": "@io see source code"
    },
    {
      "name": "test_baseline_counts",
      "kind": "function",
      "signature": "def test_baseline_counts(...)",
      "lines": [
        64,
        96
      ],
      "summary_l0": "Function test_baseline_counts",
      "contract_l1": "@io see source code"
    },
    {
      "name": "test_import_auto_collector",
      "kind": "function",
      "signature": "def test_import_auto_collector(...)",
      "lines": [
        98,
        122
      ],
      "summary_l0": "Function test_import_auto_collector",
      "contract_l1": "@io see source code"
    },
    {
      "name": "test_log_context_operation",
      "kind": "function",
      "signature": "def test_log_context_operation(...)",
      "lines": [
        124,
        164
      ],
      "summary_l0": "Function test_log_context_operation",
      "contract_l1": "@io see source code"
    },
    {
      "name": "test_create_trace",
      "kind": "function",
      "signature": "def test_create_trace(...)",
      "lines": [
        166,
        226
      ],
      "summary_l0": "Function test_create_trace",
      "contract_l1": "@io see source code"
    },
    {
      "name": "test_queue_embedding",
      "kind": "function",
      "signature": "def test_queue_embedding(...)",
      "lines": [
        228,
        266
      ],
      "summary_l0": "Function test_queue_embedding",
      "contract_l1": "@io see source code"
    },
    {
      "name": "test_create_evidence_pack",
      "kind": "function",
      "signature": "def test_create_evidence_pack(...)",
      "lines": [
        268,
        318
      ],
      "summary_l0": "Function test_create_evidence_pack",
      "contract_l1": "@io see source code"
    },
    {
      "name": "test_verify_all_sources",
      "kind": "function",
      "signature": "def test_verify_all_sources(...)",
      "lines": [
        320,
        361
      ],
      "summary_l0": "Function test_verify_all_sources",
      "contract_l1": "@io see source code"
    },
    {
      "name": "log_pass",
      "kind": "function",
      "signature": "def log_pass(...)",
      "lines": [
        363,
        367
      ],
      "summary_l0": "Function log_pass",
      "contract_l1": "@io see source code"
    },
    {
      "name": "log_fail",
      "kind": "function",
      "signature": "def log_fail(...)",
      "lines": [
        369,
        373
      ],
      "summary_l0": "Function log_fail",
      "contract_l1": "@io see source code"
    },
    {
      "name": "print_summary",
      "kind": "function",
      "signature": "def print_summary(...)",
      "lines": [
        375,
        397
      ],
      "summary_l0": "Function print_summary",
      "contract_l1": "@io see source code"
    }
  ]
}
<!--AGTAG v1 END-->
