#!/usr/bin/env python3
"""
Production validation script.
Checks if production setup is working correctly.
"""

import os
import requests
import json
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API port from environment (default 8000)
API_PORT = int(os.getenv("API_PORT", "8000"))
API_BASE = f"http://localhost:{API_PORT}"

def check_server_health():
    """Check if server is running and healthy"""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running and healthy")
            return True
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return False

def check_configuration():
    """Check if configuration is valid"""
    try:
        response = requests.get(f"{API_BASE}/api/slack/stats")
        if response.status_code == 200:
            print("✅ Configuration is valid")
            return True
        else:
            print(f"❌ Configuration error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Configuration check failed: {e}")
        return False

def test_small_sync():
    """Test a small sync (last 1 hour)"""
    print("🔄 Testing small sync (1 hour)...")
    try:
        response = requests.post(f"{API_BASE}/api/slack/sync?hours_ago=1", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Sync successful: {data['fetch']['new_messages']} new messages")
            return True
        else:
            print(f"❌ Sync failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Sync error: {e}")
        return False

def check_inbox_quality():
    """Check if inbox prioritization looks reasonable"""
    try:
        response = requests.get(f"{API_BASE}/api/slack/inbox?view=all&limit=20")
        if response.status_code != 200:
            print("❌ Cannot fetch inbox")
            return False
        
        data = response.json()
        messages = data.get('messages', [])
        
        if not messages:
            print("⚠️  No messages found - this might be normal for a new setup")
            return True
        
        print(f"📊 Found {len(messages)} messages")
        
        # Check for reasonable distribution
        high_priority = [m for m in messages if m['priority_score'] >= 70]
        needs_response = [m for m in messages if m['priority_score'] >= 90]
        
        print(f"   - High priority (70+): {len(high_priority)}")
        print(f"   - Needs response (90+): {len(needs_response)}")
        
        # Check for @mentions
        your_user_id = "U_YOUR_USER_ID"  # Update this
        mentions = [m for m in messages if f"<@{your_user_id}>" in m['text']]
        if mentions:
            high_mention_scores = [m for m in mentions if m['priority_score'] >= 80]
            print(f"   - @mentions: {len(mentions)} (high priority: {len(high_mention_scores)})")
        
        # Show sample messages
        print("\n📋 Sample messages:")
        for i, msg in enumerate(messages[:3]):
            print(f"   [{msg['priority_score']}] {msg['text'][:60]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Inbox check failed: {e}")
        return False

def check_costs():
    """Estimate costs based on current usage"""
    try:
        response = requests.get(f"{API_BASE}/api/slack/stats")
        if response.status_code == 200:
            stats = response.json()
            total_messages = stats.get('total_messages', 0)
            
            # Rough cost estimate: $0.001 per 500 messages
            daily_cost = (total_messages / 500) * 0.001
            monthly_cost = daily_cost * 30
            
            print(f"💰 Cost estimate:")
            print(f"   - Total messages: {total_messages}")
            print(f"   - Daily cost: ~${daily_cost:.3f}")
            print(f"   - Monthly cost: ~${monthly_cost:.2f}")
            
            if monthly_cost > 50:
                print("⚠️  High cost detected - consider reducing sync frequency")
            
            return True
        else:
            print("❌ Cannot fetch stats")
            return False
    except Exception as e:
        print(f"❌ Cost check failed: {e}")
        return False

def main():
    """Run all production validation checks"""
    print("🔍 Production Validation")
    print("=" * 50)
    
    checks = [
        ("Server Health", check_server_health),
        ("Configuration", check_configuration),
        ("Small Sync", test_small_sync),
        ("Inbox Quality", check_inbox_quality),
        ("Cost Estimate", check_costs),
    ]
    
    passed = 0
    total = len(checks)
    
    for name, check_func in checks:
        print(f"\n🔍 {name}...")
        if check_func():
            passed += 1
        else:
            print(f"❌ {name} failed")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 Production setup looks good!")
        print("\nNext steps:")
        print(f"1. Run full sync: curl -X POST 'http://localhost:{API_PORT}/api/slack/sync?hours_ago=24'")
        print("2. Check inbox: python scripts/check_inbox.py")
        print("3. Set up automation (cron or PM2)")
    else:
        print("❌ Some checks failed. Review the errors above.")
        print("\nTroubleshooting:")
        print("1. Check server logs: tail -f logs/slack_intelligence.log")
        print("2. Verify .env configuration")
        print("3. Ensure bot is added to channels")
        sys.exit(1)

if __name__ == "__main__":
    main()
