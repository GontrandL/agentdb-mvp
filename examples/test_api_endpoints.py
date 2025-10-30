"""
Task 4: Dashboard API Endpoints Integration Test.

Tests /context/build, /zoom/expand, and /zoom/symbol endpoints
with AgentDB progressive disclosure.
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8100"


def estimate_tokens(text: str) -> int:
    """Rough token estimation."""
    return len(text) // 4


def test_context_build():
    """Test 4.1: /context/build endpoint with sample file."""
    print("=" * 70)
    print(" TEST 4.1: /context/build Endpoint")
    print("=" * 70)
    print()

    url = f"{BASE_URL}/context/build"
    payload = {
        "role": "code_fixer",
        "custom_query": "calculator functions",
        "budget_tokens": 1000,
        "include_ocr": False
    }

    print(f"Request: POST {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()

    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Context build successful!")
            print(f"   Pack ID: {data.get('pack_id', 'N/A')}")
            print(f"   Role: {data.get('role', 'N/A')}")
            print(f"   Budget: {data.get('budget_tokens', 0)} tokens")
            print(f"   Actual: {data.get('actual_tokens', 0)} tokens")
            print(f"   Compression: Level {data.get('compression_level', 0)}")
            print(f"   Items: {len(data.get('items', []))}")

            # Check if our sample file is included
            items = data.get('items', [])
            sample_file_found = False
            for item in items:
                if 'calculator' in str(item).lower():
                    sample_file_found = True
                    print(f"   ✅ Sample calculator file found in context!")
                    break

            if not sample_file_found:
                print(f"   ⚠️  Sample file not found in context (may need custom query adjustment)")

            # Calculate token savings
            budget = data.get('budget_tokens', 1000)
            actual = data.get('actual_tokens', 0)
            savings = ((budget - actual) / budget) * 100 if budget > 0 else 0
            print(f"   Token savings: {savings:.1f}%")

            return True, data
        else:
            print(f"❌ Request failed: {response.text[:200]}")
            return False, {}

    except Exception as e:
        print(f"❌ Error: {e}")
        return False, {}


def test_zoom_expand():
    """Test 4.2: /zoom/expand endpoint."""
    print()
    print("=" * 70)
    print(" TEST 4.2: /zoom/expand Endpoint")
    print("=" * 70)
    print()

    # First, get file_id for sample_calculator.py from database
    # For this test, we'll use file_id=1 (our sample file should be first)

    url = f"{BASE_URL}/zoom/expand"
    payload = {
        "file_id": 1,
        "lines": "8-21",  # add function
        "padding": 5
    }

    print(f"Request: POST {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()

    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Zoom expand successful!")
            print(f"   Start line: {data.get('start_line', 'N/A')}")
            print(f"   End line: {data.get('end_line', 'N/A')}")
            content = data.get('content', '')
            tokens = estimate_tokens(content)
            print(f"   Content length: {len(content)} chars")
            print(f"   Estimated tokens: {tokens}")
            print(f"   File path: {data.get('file_path', 'N/A')}")

            # Show snippet
            if content:
                snippet = content[:200] + "..." if len(content) > 200 else content
                print(f"   Snippet:\n{snippet}")

            return True, data
        else:
            print(f"❌ Request failed: {response.text[:200]}")
            return False, {}

    except Exception as e:
        print(f"❌ Error: {e}")
        return False, {}


def test_zoom_symbol():
    """Test 4.3: /zoom/symbol endpoint."""
    print()
    print("=" * 70)
    print(" TEST 4.3: /zoom/symbol Endpoint")
    print("=" * 70)
    print()

    url = f"{BASE_URL}/zoom/symbol"
    payload = {
        "symbol": "add",
        "file_path": "examples/sample_calculator.py"
    }

    print(f"Request: POST {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()

    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Zoom symbol successful!")
            print(f"   Symbol: {data.get('symbol', 'N/A')}")
            print(f"   Kind: {data.get('kind', 'N/A')}")

            definition = data.get('definition', {})
            print(f"   Definition:")
            print(f"     File: {definition.get('file_path', 'N/A')}")
            print(f"     Lines: {definition.get('start_line', '?')}-{definition.get('end_line', '?')}")

            # Check for progressive disclosure data
            if 'summary_l0' in data or 'contract_l1' in data:
                print(f"   ✅ Progressive disclosure data present!")
                if 'summary_l0' in data:
                    print(f"     L0 (overview): {data['summary_l0']}")
                if 'contract_l1' in data:
                    print(f"     L1 (contract): {data['contract_l1']}")
                if 'pseudocode_l2' in data:
                    print(f"     L2 (pseudocode): {data['pseudocode_l2'][:100]}...")
            else:
                print(f"   ⚠️  Progressive disclosure data not found (may require AgentDB integration)")

            # Token estimate
            content = data.get('content', '')
            tokens = estimate_tokens(content)
            print(f"   Content tokens (estimated): {tokens}")

            return True, data
        else:
            print(f"❌ Request failed: {response.text[:200]}")
            return False, {}

    except Exception as e:
        print(f"❌ Error: {e}")
        return False, {}


def main():
    """Run all Task 4 API endpoint tests."""
    print("\n")
    print("="*70)
    print(" TASK 4: DASHBOARD API ENDPOINTS INTEGRATION TEST")
    print("="*70)
    print(f" Test started: {datetime.now().isoformat()}")
    print(f" Base URL: {BASE_URL}")
    print("="*70)
    print()

    results = {}

    # Test 4.1
    success_4_1, data_4_1 = test_context_build()
    results['test_4_1_context_build'] = success_4_1

    # Test 4.2
    success_4_2, data_4_2 = test_zoom_expand()
    results['test_4_2_zoom_expand'] = success_4_2

    # Test 4.3
    success_4_3, data_4_3 = test_zoom_symbol()
    results['test_4_3_zoom_symbol'] = success_4_3

    # Summary
    print()
    print("=" * 70)
    print(" TASK 4 SUMMARY")
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
        print("🎉 ALL TASK 4 TESTS PASSED!")
    else:
        print(f"⚠️  {total - passed} test(s) failed")

    print("=" * 70)

    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
