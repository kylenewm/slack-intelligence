#!/bin/bash
# Comprehensive local testing script

echo "=========================================================================="
echo "🧪 COMPREHENSIVE LOCAL TESTING"
echo "=========================================================================="
echo ""

cd /Users/knewman/Downloads/slack-intelligence
source venv/bin/activate

echo "Step 1: Validate Configuration"
echo "----------------------------------------------------------------------"
python scripts/test_production_features.py
echo ""
read -p "Press Enter to continue to Step 2..."

echo ""
echo "=========================================================================="
echo "Step 2: Manual Sync Test"
echo "----------------------------------------------------------------------"
echo "This will:"
echo "  - Fetch messages from Slack"
echo "  - Prioritize with AI"
echo "  - Send alerts for score >= 90"
echo "  - Extract action items for score >= 80"
echo "  - Sync to Notion"
echo ""
read -p "Press Enter to run sync..."
echo ""

python scripts/sync_once.py

echo ""
read -p "Press Enter to continue to Step 3..."

echo ""
echo "=========================================================================="
echo "Step 3: Check Inbox"
echo "----------------------------------------------------------------------"
python scripts/check_inbox.py

echo ""
read -p "Press Enter to continue to Step 4..."

echo ""
echo "=========================================================================="
echo "Step 4: Test Jira Integration (with Context Enrichment)"
echo "----------------------------------------------------------------------"
echo "This will create a Jira ticket with thread context included"
echo ""
read -p "Skip Jira test? (y/n, default n): " skip_jira

if [ "$skip_jira" != "y" ]; then
    python scripts/create_jira_ticket.py
fi

echo ""
echo "=========================================================================="
echo "Step 5: Start API with Auto-Sync"
echo "----------------------------------------------------------------------"
echo "Now we'll start the API server with auto-sync enabled."
echo "You'll see auto-sync run every 15 minutes automatically."
echo ""
echo "Press Ctrl+C to stop the server when done testing."
echo ""
read -p "Press Enter to start API server..."
echo ""

uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

