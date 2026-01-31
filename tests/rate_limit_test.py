import time
import httpx
import sys

API_URL = "http://localhost:8000/api/tickets"
LIMIT = 30  # configured limit per minute
TEST_COUNT = 35  # Should verify 30 success + 5 failures

def test_rate_limit():
    print(f"🛑 TESTING RATE LIMIT: Sending {TEST_COUNT} requests (Limit: {LIMIT}/min)...")
    
    success = 0
    blocked = 0
    errors = 0
    
    with httpx.Client(timeout=5.0) as client:
        for i in range(TEST_COUNT):
            try:
                # Fast requests
                resp = client.post(API_URL, json={"customer_complaint": f"Rate limit test {i}"})
                
                if resp.status_code == 201:
                    print(f"   req #{i+1}: 201 Created")
                    success += 1
                elif resp.status_code == 429:
                    print(f"   req #{i+1}: 🔴 429 Too Many Requests (Blocked as expected)")
                    blocked += 1
                else:
                    print(f"   req #{i+1}: ⚠️ Unexpected {resp.status_code}")
                    errors += 1
            except Exception as e:
                print(f"   req #{i+1}: ❌ Error: {e}")
                errors += 1
                
    print("-" * 40)
    print(f"✅ Success (Allowed): {success}")
    print(f"🛡️ Blocked (429):     {blocked}")
    print(f"❌ Errors:            {errors}")
    print("-" * 40)
    
    if blocked > 0:
        print("🎉 Rate Limiting is WORKING!")
        sys.exit(0)
    else:
        print("⚠️ Rate Limiting NOT detected (Check config or IP detection)")
        sys.exit(1)

if __name__ == "__main__":
    test_rate_limit()
