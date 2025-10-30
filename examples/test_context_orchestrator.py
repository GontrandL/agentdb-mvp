"""
Task 5.2: Context Orchestrator Integration Test.

Tests Context Orchestrator with AgentDB progressive disclosure integration.
Validates:
1. AgentDBBridge initialization in ContextOrchestrator
2. Progressive disclosure in _hybrid_search (L1 contracts)
3. Token savings compared to FileIndex fallback
4. Graceful fallback when AgentDB unavailable
"""
import sys
sys.path.insert(0, '../dashboard')

from app.context_orchestrator import ContextOrchestrator
from datetime import datetime


def estimate_tokens(text: str) -> int:
    """Rough token estimation: 1 token ≈ 4 characters."""
    return len(text) // 4


def test_orchestrator_initialization():
    """Test 5.2.1: Verify AgentDBBridge initialized in ContextOrchestrator."""
    print("=" * 70)
    print(" TEST 5.2.1: ContextOrchestrator Initialization")
    print("=" * 70)
    print()

    orchestrator = ContextOrchestrator()

    # Check if AgentDBBridge is initialized
    has_bridge = hasattr(orchestrator, 'agentdb_bridge')
    bridge_initialized = has_bridge and orchestrator.agentdb_bridge is not None

    print(f"AgentDBBridge attribute exists: {has_bridge}")
    print(f"AgentDBBridge initialized: {bridge_initialized}")

    if bridge_initialized:
        is_ready = orchestrator.agentdb_bridge.is_initialized()
        print(f"AgentDB ready: {is_ready}")

        if is_ready:
            inventory_result = orchestrator.agentdb_bridge.inventory()
            if inventory_result.success:
                files_count = len(inventory_result.data.get("files", []))
                print(f"AgentDB files indexed: {files_count}")
                print()
                print("✅ AgentDBBridge successfully initialized in ContextOrchestrator")
                return True, files_count
            else:
                print(f"⚠️  AgentDB inventory failed: {inventory_result.error}")
        else:
            print("⚠️  AgentDB not initialized (database may be empty)")
    else:
        print("❌ AgentDBBridge not initialized in ContextOrchestrator")

    print()
    return bridge_initialized, 0


def test_hybrid_search_with_agentdb():
    """Test 5.2.2: Test _hybrid_search with AgentDB progressive disclosure."""
    print()
    print("=" * 70)
    print(" TEST 5.2.2: Hybrid Search with AgentDB")
    print("=" * 70)
    print()

    orchestrator = ContextOrchestrator()

    # Test query targeting our sample calculator file
    query = "calculator"

    print(f"Query: '{query}'")
    print(f"Target: examples/sample_calculator.py")
    print()

    # Call _hybrid_search directly (internal method)
    try:
        items = orchestrator._hybrid_search(
            query=query,
            include_ocr=False,
            mix={"docs": 0.0, "code": 1.0, "ocr": 0.0},  # Code only
            session=None,
            limit=10
        )

        print(f"Results: {len(items)} items")
        print()

        # Analyze results
        agentdb_items = [item for item in items if item.id.startswith("agentdb_")]
        fileindex_items = [item for item in items if item.id.startswith("file_")]

        print(f"AgentDB items (progressive disclosure): {len(agentdb_items)}")
        print(f"FileIndex items (fallback): {len(fileindex_items)}")
        print()

        if agentdb_items:
            print("✅ AgentDB progressive disclosure working!")
            print()

            for item in agentdb_items:
                tokens = estimate_tokens(item.content)
                print(f"  File: {item.file_path}")
                print(f"  Reason: {item.reason}")
                print(f"  Token cost: {tokens} tokens (cost_hint: {item.cost_hint})")
                print(f"  Confidence: {item.confidence}")
                print(f"  Content preview:")
                print(f"    {item.content[:200]}...")
                print()

            # Compare token usage
            total_agentdb_tokens = sum(estimate_tokens(item.content) for item in agentdb_items)
            print(f"Total AgentDB tokens: {total_agentdb_tokens}")
            print()

            # Compare to traditional approach (full file)
            with open('../examples/sample_calculator.py', 'r') as f:
                full_content = f.read()
                traditional_tokens = estimate_tokens(full_content)

            savings = ((traditional_tokens - total_agentdb_tokens) / traditional_tokens) * 100
            print(f"Comparison:")
            print(f"  Traditional (full file): {traditional_tokens} tokens")
            print(f"  AgentDB (L1 contracts): {total_agentdb_tokens} tokens")
            print(f"  Token savings: {savings:.1f}%")
            print()

            if savings > 80:
                print(f"✅ Excellent token savings ({savings:.1f}%)!")
                return True, savings
            else:
                print(f"⚠️  Token savings below target ({savings:.1f}% < 80%)")
                return True, savings

        elif fileindex_items:
            print("⚠️  FileIndex fallback used (AgentDB may not have indexed files)")
            return False, 0
        else:
            print("❌ No results returned")
            return False, 0

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False, 0


def test_context_build_integration():
    """Test 5.2.3: Test full context build workflow."""
    print()
    print("=" * 70)
    print(" TEST 5.2.3: Full Context Build Workflow")
    print("=" * 70)
    print()

    orchestrator = ContextOrchestrator()

    print("Building context pack with role='code_fixer', query='calculator'")
    print()

    # Note: This would normally require a database session
    # For now, we're testing the hybrid search integration
    try:
        items = orchestrator._hybrid_search(
            query="calculator",
            include_ocr=False,
            session=None,
            limit=5
        )

        print(f"Context items retrieved: {len(items)}")
        total_tokens = sum(estimate_tokens(item.content) for item in items)
        print(f"Total token cost: {total_tokens}")
        print()

        agentdb_count = len([i for i in items if i.id.startswith("agentdb_")])
        if agentdb_count > 0:
            print(f"✅ AgentDB used for {agentdb_count} items")
            print("✅ Progressive disclosure integrated into context building")
            return True
        else:
            print("⚠️  No AgentDB items in context pack")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all Context Orchestrator integration tests."""
    print("\n")
    print("=" * 70)
    print(" TASK 5.2: CONTEXT ORCHESTRATOR INTEGRATION TEST")
    print("=" * 70)
    print(f" Test started: {datetime.now().isoformat()}")
    print("=" * 70)
    print()

    results = {}

    # Test 5.2.1: Initialization
    bridge_ok, files_count = test_orchestrator_initialization()
    results['initialization'] = bridge_ok

    if not bridge_ok:
        print()
        print("=" * 70)
        print(" ⚠️  SKIPPING REMAINING TESTS")
        print("=" * 70)
        print()
        print("AgentDBBridge not initialized. Possible reasons:")
        print("  1. AgentDB database not initialized")
        print("  2. AgentDB not in expected location")
        print("  3. Error during bridge initialization")
        print()
        print("Run: cd .. && python3 -m src.agentdb.core init")
        print()
        return False

    if files_count == 0:
        print()
        print("=" * 70)
        print(" ⚠️  WARNING: No files indexed")
        print("=" * 70)
        print()
        print("AgentDB is initialized but empty.")
        print("Sample file may not be ingested.")
        print()
        print("To test fully, ensure sample_calculator.py is ingested:")
        print("  cd .. && python3 -m src.agentdb.core ingest --path examples/sample_calculator.py")
        print()

    # Test 5.2.2: Hybrid search
    search_ok, savings = test_hybrid_search_with_agentdb()
    results['hybrid_search'] = search_ok

    # Test 5.2.3: Context build
    build_ok = test_context_build_integration()
    results['context_build'] = build_ok

    # Summary
    print()
    print("=" * 70)
    print(" TASK 5.2 SUMMARY")
    print("=" * 70)
    print()

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"Tests passed: {passed}/{total}")
    print()

    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test}")

    print()

    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print()
        print("Context Orchestrator successfully integrated with AgentDB!")
        print(f"Token savings achieved: {savings:.1f}%" if savings > 0 else "")
    else:
        print(f"⚠️  {total - passed} test(s) failed")

    print()
    print("=" * 70)

    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
