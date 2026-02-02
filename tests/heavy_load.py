import time
import httpx
import concurrent.futures
import random
import sys
from collections import Counter

# Configuration
API_URL = "http://localhost:8000/api/tickets"
TOTAL_REQUESTS = 200  # High volume to flood the queue
CONCURRENCY = 20      # Parallel requests
POLL_INTERVAL = 2     # Polling status check interval

# Random complaints to avoid caching implications (if any)
COMPLAINTS = [
    "The system is slow!",
    "I was charged double.",
    "Can I change my username?",
    "App crashes on startup.",
    "Where is the dark mode?",
    "Payment failed with error 504.",
    "I want a refund now!",
    "Is this service free?",
    "Login button is broken.",
    "API documentation is unclear."
]

def send_ticket(i):
    """Send a single ticket creation request."""
    complaint = random.choice(COMPLAINTS) + f" [LoadTest-{i}]"
    try:
        start = time.time()
        resp = httpx.post(API_URL, json={"customer_complaint": complaint}, timeout=10.0)
        duration = time.time() - start
        return {
            "status_code": resp.status_code,
            "duration": duration,
            "id": resp.json().get("id") if resp.status_code == 201 else None
        }
    except Exception as e:
        return {"status_code": "Error", "duration": 0, "error": str(e)}

def run_load_test():
    print(f"🔥 STARTING HEAVY LOAD TEST: {TOTAL_REQUESTS} requests, {CONCURRENCY} threads")
    print(f"🎯 Target: API Throughput & Queue Resilience (Gemini Rate Limit: 60/min)")
    print("-" * 60)

    # 1. Blast API with requests
    results = []
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = {executor.submit(send_ticket, i): i for i in range(TOTAL_REQUESTS)}
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
            if len(results) % 50 == 0:
                print(f"   ...sent {len(results)}/{TOTAL_REQUESTS} requests")

    total_time = time.time() - start_time
    success_count = sum(1 for r in results if r["status_code"] == 201)
    blocked_count = sum(1 for r in results if r["status_code"] == 429)
    error_count = len(results) - success_count - blocked_count
    avg_duration = sum(r["duration"] for r in results) / len(results)

    print("-" * 60)
    print(f"✅ Ingestion Complete in {total_time:.2f}s")
    print(f"   Throughput: {TOTAL_REQUESTS / total_time:.2f} req/sec")
    print(f"   Success: {success_count} (201 Created)")
    print(f"   Blocked: {blocked_count} (429 Too Many Requests) - RATE LIMIT ACTIVE")
    print(f"   Errors:  {error_count} (5xx/Oth)")
    print(f"   Avg Latency: {avg_duration * 1000:.2f}ms")
    print("-" * 60)

    if success_count == 0:
        print("❌ No tickets created. Aborting.")
        return

    # 2. Monitor Processing Queue
    print("\n🧐 Monitoring Background Worker Processing...")
    print("   (Expect slowdown/fallbacks due to Gemini Rate Limit)")
    
    # Poll count of statuses until all processed
    # We'll poll for 60 seconds max
    for i in range(30):
        try:
            # Using list endpoint to get counts (not implemented ideally for stats, but works)
            # Actually better to query DB directly or just check a sample. 
            # Let's hit the list endpoint with limit=1 just to check stats if I implemented total count logic?
            # List endpoint returns "total".
            
            resp_completed = httpx.get(f"{API_URL}?status=completed&limit=1")
            resp_failed = httpx.get(f"{API_URL}?status=failed&limit=1")
            resp_pending = httpx.get(f"{API_URL}?status=pending&limit=1")
            resp_processing = httpx.get(f"{API_URL}?status=processing&limit=1")
            
            total_completed = resp_completed.json().get("total", 0)
            total_failed = resp_failed.json().get("total", 0)
            total_pending = resp_pending.json().get("total", 0)
            total_processing = resp_processing.json().get("total", 0)
            
            print(f"   [{i*2}s] Pending: {total_pending} | Processing: {total_processing} | Completed: {total_completed} | Failed: {total_failed}")
            
            if total_pending == 0 and total_processing == 0:
                print("\n✅ All tickets processed!")
                break
                
            time.sleep(2)
        except Exception as e:
            print(f"   Error polling status: {e}")
            time.sleep(2)

if __name__ == "__main__":
    # Safety Check
    if "--force" not in sys.argv:
        print(f"\n⚠ WARNING: This is a HEAVY LOAD test ({TOTAL_REQUESTS} requests).")
        print("   This WILL trigger AI Rate Limits and likely default to 'fallback'.")
        response = input(f"   Are you sure you want to proceed? (y/N): ").strip().lower()
        if response != "y":
            print("❌ Aborted by user.")
            sys.exit(0)
            
    run_load_test()
