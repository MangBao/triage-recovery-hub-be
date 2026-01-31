#!/bin/bash

# Production Verification Script for Triage & Recovery Hub
# Based on docs/DEMO_SCRIPT.md

echo "🚀 Starting Production Verification..."

# Base URL
API_URL="http://localhost:8000"

# Function to check status code
check_status() {
    if [ $1 -eq 0 ]; then
        echo -e "✅ Command success"
    else
        echo -e "❌ Command failed"
        exit 1
    fi
}

echo "------------------------------------------------"
echo "Scene 1: Health Check"
echo "------------------------------------------------"
curl -s --fail "$API_URL/health" | grep "ok"
check_status $?

echo "------------------------------------------------"
echo "Scene 2: Create Ticket 1 - Angry Customer (Billing)"
echo "------------------------------------------------"
# Capture ticket ID from creation response
TICKET1_RESPONSE=$(curl -s --fail -X POST "$API_URL/api/tickets" \
  -H "Content-Type: application/json" \
  -d '{"customer_complaint":"I was charged $500 THREE TIMES for the same order! Order #ABC123. This is RIDICULOUS and I demand an IMMEDIATE refund! Very frustrated!!!"}')
check_status $?
echo "$TICKET1_RESPONSE"
TICKET1_ID=$(echo "$TICKET1_RESPONSE" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Created Ticket ID: $TICKET1_ID"

echo "------------------------------------------------"
echo "Scene 3: Create Tickets 2 & 3"
echo "------------------------------------------------"
echo "Creating Technical Issue..."
curl -s --fail -X POST "$API_URL/api/tickets" \
  -H "Content-Type: application/json" \
  -d '{"customer_complaint":"App keeps crashing when uploading photos. Error 500. iPhone 15, latest iOS."}'
check_status $?

echo "Creating Feature Request..."
curl -s --fail -X POST "$API_URL/api/tickets" \
  -H "Content-Type: application/json" \
  -d '{"customer_complaint":"Love your product! Would be great to have dark mode. Thanks!"}'
check_status $?

echo "------------------------------------------------"
echo "Scene 4: Waiting 5s for AI Processing..."
echo "------------------------------------------------"
sleep 5

echo "Checking AI Results (Limit 10)..."
curl -s --fail "$API_URL/api/tickets?limit=10" | python -m json.tool
check_status $?

echo "------------------------------------------------"
echo "Scene 5: Filter High Urgency"
echo "------------------------------------------------"
curl -s --fail "$API_URL/api/tickets?urgency=High" | python -m json.tool
check_status $?

echo "------------------------------------------------"
echo "Scene 6: Agent Workflow (Edit & Resolve Ticket $TICKET1_ID)"
echo "------------------------------------------------"
# Use captured ticket ID instead of hardcoded "1"
echo "Updating Ticket $TICKET1_ID..."
curl -s --fail -X PATCH "$API_URL/api/tickets/$TICKET1_ID" \
  -H "Content-Type: application/json" \
  -d '{"agent_edited_response":"Dear customer, I apologize for this error. Full refund of $1500 processed. Please allow 3-5 days."}'
check_status $?

echo "Resolving Ticket $TICKET1_ID..."
curl -s --fail -X POST "$API_URL/api/tickets/$TICKET1_ID/resolve?agent_id=agent-bao"
check_status $?

echo "------------------------------------------------"
echo "Scene 7: Final Summary"
echo "------------------------------------------------"
curl -s --fail "$API_URL/api/tickets?limit=10" | python -m json.tool
check_status $?

echo "🎉 Verification Complete!"
