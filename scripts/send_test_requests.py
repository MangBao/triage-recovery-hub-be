import requests
import time
import json

BASE_URL = "http://localhost:8000/api/tickets"

# 5 Brand New Scenarios
test_cases = [
    "My delivery arrived but it is missing the main power cable and the remote.",
    "I placed an order an hour ago but changed my mind. Can I cancel it before it ships?",
    "The application freezes completely when I try to proceed to checkout.",
    "I need to change the email address associated with my account. The old one is deleted.",
    "Do you accept Bitcoin or Ethereum for subscription payments?"
]

print(f"🚀 Sending 5 FRESH test requests to {BASE_URL}...\n")

for i, complaint in enumerate(test_cases, 1):
    payload = {"customer_complaint": complaint}
    try:
        response = requests.post(BASE_URL, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"✅ [{i}/{len(test_cases)}] Created Ticket #{data['id']}")
        print(f"   Complaint: {complaint[:50]}...")
        print(f"   Status: {data['status']}")
    except Exception as e:
        print(f"❌ [{i}/{len(test_cases)}] Failed: {e}")
    time.sleep(1)

print("\n✨ Data seeded into fresh database! Monitoring worker...")
