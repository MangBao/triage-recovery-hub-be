import time
import httpx
import json
import sys
from typing import List, Dict, Any

# Configuration
API_URL = "http://localhost:8000/api/tickets"
POLL_INTERVAL = 3  # seconds
MAX_RETRIES = 10   # 30 seconds max wait

# Test Scenarios
SCENARIOS = [
    {
        "name": "1. Urgent Billing Issue",
        "complaint": "I was charged $500 TWICE for the same transaction! This is unauthorized. Refund me immediately or I call my lawyer!",
        "expected_category": "Billing",
        "expected_urgency": "High"
    },
    {
        "name": "2. Technical Crash",
        "complaint": "The app keeps force closing when I try to upload a profile picture. I'm on iPhone 14 Pro, iOS 17.2.",
        "expected_category": "Technical",
        "expected_urgency": "Medium"  # or High
    },
    {
        "name": "3. Feature Request (Positive)",
        "complaint": "I really love the new dashboard! It would be even better if we could export the reports to PDF. Thanks!",
        "expected_category": "Feature Request",
        "expected_urgency": "Low"
    },
    {
        "name": "4. Vietnamese Complaint (Multilingual)",
        "complaint": "Ứng dụng bị lỗi không thanh toán được. Tôi đã thử thẻ Visa và Momo đều báo thất bại. Sửa gấp giúp tôi.",
        "expected_category": "Technical", # or Billing
        "expected_urgency": "High"
    },
    {
        "name": "5. Short/Ambiguous",
        "complaint": "Not working.",
        "expected_category": "Technical",
        "expected_urgency": "Medium" # or Low
    },
    {
        "name": "6. Complex Mixed Issue",
        "complaint": "I want a refund because the feature I paid for (export PDF) is not working at all. I also think you should add dark mode.",
        "expected_category": "Billing", # Hybrid, usually Billing takes precedence or Tech
        "expected_urgency": "Medium"
    }
]

def run_test():
    """Run stress test and return True if all passed, False otherwise."""
    print(f"🚀 Starting Stress Test with {len(SCENARIOS)} scenarios...\n")
    results = []

    with httpx.Client(timeout=30.0) as client:
        # Check Health
        try:
            resp = client.get("http://localhost:8000/health")
            if resp.status_code != 200:
                print("❌ API is not healthy. Aborting.")
                return False
            print("✅ Health Check OK\n")
        except Exception as e:
            print(f"❌ Failed to reach API: {e}")
            return False

        for scenario in SCENARIOS:
            print(f"Testing: {scenario['name']}")
            print(f"📝 Input: \"{scenario['complaint'][:50]}...\"")
            
            try:
                # 1. Create Ticket
                resp = client.post(API_URL, json={"customer_complaint": scenario['complaint']})
                if resp.status_code != 201:
                    print(f"❌ Failed to create ticket: {resp.text}")
                    results.append({"name": scenario['name'], "status": "Failed"})
                    continue
                
                ticket = resp.json()
                ticket_id = ticket["id"]
                print(f"   Created Ticket ID: {ticket_id} (Status: {ticket['status']})")
                
                # 2. Poll for completion
                final_ticket = None
                for i in range(MAX_RETRIES):
                    time.sleep(POLL_INTERVAL)
                    resp = client.get(f"{API_URL}/{ticket_id}")
                    if resp.status_code != 200:
                        continue
                    
                    data = resp.json()
                    if data["status"] in ["completed", "failed"]:
                        final_ticket = data
                        break
                    print(f"   ...polling ({i+1}/{MAX_RETRIES}) status={data['status']}")
                
                # 3. Analyze Result
                if final_ticket:
                    status_icon = "✅" if final_ticket["status"] == "completed" else "❌"
                    print(f"   {status_icon} Result: Status={final_ticket['status']}")
                    print(f"      Category: {final_ticket['category']} (Expected: {scenario['expected_category']})")
                    print(f"      Urgency:  {final_ticket['urgency']} (Expected: {scenario['expected_urgency']})")
                    print(f"      Sentiment: {final_ticket['sentiment_score']}/10")
                    print(f"      Response: \"{final_ticket['ai_draft_response'][:60]}...\"")
                    
                    results.append({
                        "name": scenario['name'], 
                        "status": "Pass" if final_ticket["status"] == "completed" else "Fail",
                        "category": final_ticket['category'],
                        "urgency": final_ticket['urgency']
                    })
                else:
                    print("❌ Timeout waiting for processing")
                    results.append({"name": scenario['name'], "status": "Timeout"})
            
            except Exception as e:
                print(f"❌ Exception: {e}")
                results.append({"name": scenario['name'], "status": "Error"})
            
            print("-" * 50)
            time.sleep(2.0) # Avoid rate limits between scenarios

    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 60)
    print(f"{'Scenario':<35} | {'Status':<10} | {'Category':<15} | {'Urgency':<10}")
    print("-" * 60)
    for r in results:
        cat = r.get('category', 'N/A') or 'N/A'
        urg = r.get('urgency', 'N/A') or 'N/A'
        print(f"{r['name']:<35} | {r['status']:<10} | {cat:<15} | {urg:<10}")
    print("=" * 60)
    
    # Determine overall success
    failed_statuses = {"Failed", "Timeout", "Error", "Fail"}
    success = all(r.get("status") not in failed_statuses for r in results)
    return success

if __name__ == "__main__":
    success = run_test()
    if success:
        print("🎉 All scenarios passed!")
        sys.exit(0)
    else:
        print("⚠️ Some scenarios failed.")
        sys.exit(1)
