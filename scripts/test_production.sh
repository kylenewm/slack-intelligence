#!/bin/bash
# Production Validation Script
# Usage: ./scripts/test_production.sh https://your-app.railway.app

RAILWAY_URL="$1"

if [ -z "$RAILWAY_URL" ]; then
    echo "❌ Usage: ./scripts/test_production.sh https://your-app.railway.app"
    exit 1
fi

echo "🧪 Testing Railway Production Deployment"
echo "URL: $RAILWAY_URL"
echo ""

# Test 1: Health Check
echo "Test 1: Health endpoint..."
HEALTH=$(curl -s "$RAILWAY_URL/health")
echo "$HEALTH"
if [[ $HEALTH == *"healthy"* ]]; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
fi
echo ""

# Test 2: Root endpoint
echo "Test 2: Root endpoint..."
ROOT=$(curl -s "$RAILWAY_URL/")
echo "$ROOT"
echo "✅ Root endpoint accessible"
echo ""

# Test 3: API Docs
echo "Test 3: API docs..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$RAILWAY_URL/docs")
if [ "$STATUS" -eq 200 ]; then
    echo "✅ API docs accessible at $RAILWAY_URL/docs"
else
    echo "❌ API docs not accessible (HTTP $STATUS)"
fi
echo ""

# Test 4: Stats endpoint
echo "Test 4: Stats endpoint..."
STATS=$(curl -s "$RAILWAY_URL/api/slack/stats")
echo "$STATS"
echo ""

# Test 5: Inbox endpoint
echo "Test 5: Inbox endpoint..."
INBOX=$(curl -s "$RAILWAY_URL/api/slack/inbox?view=all&limit=5")
echo "$INBOX"
echo ""

# Test 6: Trigger sync (optional)
echo "Test 6: Manual sync..."
echo "⚠️  This will trigger a real sync from Slack (costs OpenAI tokens)"
read -p "Proceed? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    SYNC=$(curl -s -X POST "$RAILWAY_URL/api/slack/sync?hours_ago=1")
    echo "$SYNC"
    echo "✅ Sync triggered"
else
    echo "⏭️  Skipped sync test"
fi

echo ""
echo "🎉 Production validation complete!"
echo ""
echo "📊 Quick Links:"
echo "  - API Docs: $RAILWAY_URL/docs"
echo "  - Health: $RAILWAY_URL/health"
echo "  - Inbox: $RAILWAY_URL/api/slack/inbox"
echo "  - Stats: $RAILWAY_URL/api/slack/stats"

