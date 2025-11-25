#!/bin/bash
# Script to update .env with new production feature settings

echo "=========================================================================="
echo "📝 UPDATING .ENV FILE"
echo "=========================================================================="
echo ""

ENV_FILE="/Users/knewman/Downloads/slack-intelligence/.env"

# Check if .env exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: .env file not found at $ENV_FILE"
    exit 1
fi

echo "Found .env file: $ENV_FILE"
echo ""

# Check if settings already exist
if grep -q "AUTO_SYNC_ENABLED" "$ENV_FILE"; then
    echo "⚠️  Production settings already exist in .env"
    echo ""
    read -p "Overwrite existing settings? (y/n): " overwrite
    if [ "$overwrite" != "y" ]; then
        echo "Cancelled."
        exit 0
    fi
    # Remove old settings
    sed -i.bak '/AUTO_SYNC_ENABLED/d' "$ENV_FILE"
    sed -i.bak '/SYNC_INTERVAL_MINUTES/d' "$ENV_FILE"
    sed -i.bak '/WORK_HOURS_ONLY/d' "$ENV_FILE"
    sed -i.bak '/SLACK_ALERT_USER_ID/d' "$ENV_FILE"
fi

# Add new settings
echo "" >> "$ENV_FILE"
echo "# ============================================" >> "$ENV_FILE"
echo "# PRODUCTION FEATURES (Added $(date +%Y-%m-%d))" >> "$ENV_FILE"
echo "# ============================================" >> "$ENV_FILE"
echo "" >> "$ENV_FILE"
echo "# Auto-sync control (turn on/off to manage costs)" >> "$ENV_FILE"
echo "AUTO_SYNC_ENABLED=true" >> "$ENV_FILE"
echo "SYNC_INTERVAL_MINUTES=15" >> "$ENV_FILE"
echo "WORK_HOURS_ONLY=false" >> "$ENV_FILE"
echo "" >> "$ENV_FILE"
echo "# Slack alerts (instant DM for critical messages)" >> "$ENV_FILE"
echo "SLACK_ALERT_USER_ID=U09NR3RQZQU" >> "$ENV_FILE"
echo "" >> "$ENV_FILE"

echo "✅ Successfully updated .env file!"
echo ""
echo "Added settings:"
echo "  - AUTO_SYNC_ENABLED=true"
echo "  - SYNC_INTERVAL_MINUTES=15"
echo "  - WORK_HOURS_ONLY=false"
echo "  - SLACK_ALERT_USER_ID=U09NR3RQZQU"
echo ""
echo "=========================================================================="
echo "💡 NEXT STEPS"
echo "=========================================================================="
echo ""
echo "1. Review your .env file: cat .env"
echo "2. Start the API: uvicorn backend.main:app --reload"
echo "3. You should see: '✅ Auto-sync enabled (every 15 min)'"
echo ""
echo "To disable auto-sync: Change AUTO_SYNC_ENABLED=false"
echo ""

