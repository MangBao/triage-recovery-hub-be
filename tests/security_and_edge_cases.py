import httpx
import sys

API_URL = "http://localhost:8000/api/tickets"

# Test Cases
TEST_CASES = [
    {
        "name": "SQL Injection Attempt",
        "input": "I want a refund'; DROP TABLE tickets; --",
        "expected_status": 201, # Should be treated as a string
        "check": "safe_creation" 
    },
    {
        "name": "XSS Script Injection",
        "input": "<script>alert('hacked')</script> System is broken",
        "expected_status": 201, # API just stores text
        "check": "safe_storage"
    },
    {
        "name": "Huge Payload (10KB)",
        "input": "A" * 10000,
        "expected_status": 422, # Exceeds max_length=5000
        "check": "performance"
    },
    {
        "name": "Emoji & Unicode Spam",
        "input": "🔥🔥🔥🔥🔥🔥 ⚠️⚠️⚠️⚠️ 🐛🐛🐛🐛 Unicode: ꧁༺ ༻꧂",
        "expected_status": 201,
        "check": "encoding"
    },
    {
        "name": "Empty Input",
        "input": "",
        "expected_status": 422, # Validation error
        "check": "validation"
    }
]

def run_security_tests():
    print("🕵️ STARTING SECURITY & EDGE CASE TESTS")
    print("-" * 50)
    
    passed = 0
    failed = 0
    
    with httpx.Client(timeout=10.0) as client:
        for case in TEST_CASES:
            print(f"🧪 Testing: {case['name']}...")
            try:
                resp = client.post(API_URL, json={"customer_complaint": case['input']})
                
                if resp.status_code == case['expected_status']:
                    print(f"   ✅ PASS (Got {resp.status_code})")
                    passed += 1
                else:
                    print(f"   ❌ FAIL (Expected {case['expected_status']}, Got {resp.status_code})")
                    print(f"      Response: {resp.text[:100]}...")
                    failed += 1
                    
            except Exception as e:
                print(f"   ❌ ERROR: {e}")
                failed += 1
                
    print("-" * 50)
    print(f"Summary: {passed} PASSED | {failed} FAILED")
    
    if failed == 0:
        print("🛡️ Security & Edge Case Checks PASSED")
        sys.exit(0)
    else:
        print("⚠️ Some checks failed")
        sys.exit(1)

if __name__ == "__main__":
    run_security_tests()
