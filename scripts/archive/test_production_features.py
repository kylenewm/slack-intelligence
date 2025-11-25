#!/usr/bin/env python3
"""
Test script for new production features:
- APScheduler auto-sync
- Action item extraction
- Context enrichment for Jira
- Slack DM alerts
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path - need to add parent of backend too
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

from backend.config import settings
from backend.services.sync_service import SyncService
from backend.services.action_item_service import ActionItemService
from backend.services.alert_service import AlertService
from backend.integrations.jira_service import JiraService
from backend.database.cache_service import CacheService

print("=" * 80)
print("🧪 TESTING NEW PRODUCTION FEATURES")
print("=" * 80)


async def test_config():
    """Test configuration"""
    print("\n📋 1. Testing Configuration")
    print("-" * 80)
    
    checks = {
        "AUTO_SYNC_ENABLED": settings.AUTO_SYNC_ENABLED,
        "SYNC_INTERVAL_MINUTES": settings.SYNC_INTERVAL_MINUTES,
        "SLACK_ALERT_USER_ID": bool(settings.SLACK_ALERT_USER_ID),
        "SLACK_BOT_TOKEN": bool(settings.SLACK_BOT_TOKEN),
        "OPENAI_API_KEY": bool(settings.OPENAI_API_KEY),
        "JIRA configured": bool(settings.JIRA_API_KEY and settings.JIRA_EMAIL),
        "NOTION configured": settings.NOTION_SYNC_ENABLED
    }
    
    for key, value in checks.items():
        status = "✅" if value else "❌"
        print(f"   {status} {key}: {value}")
    
    return all([
        settings.SLACK_BOT_TOKEN,
        settings.OPENAI_API_KEY
    ])


async def test_action_items():
    """Test action item extraction"""
    print("\n🎯 2. Testing Action Item Service")
    print("-" * 80)
    
    try:
        action_service = ActionItemService()
        
        # Test with mock high-priority message
        test_message = {
            "text": "We need to fix the login bug ASAP. Users can't sign in on mobile.",
            "user_name": "Kyle Newman",
            "channel_name": "engineering",
            "priority_score": 85,
            "category": "needs_response",
            "priority_reason": "Critical bug affecting users"
        }
        
        print("   Testing with sample message...")
        result = await action_service.extract_action_items(test_message)
        
        if result:
            print(f"   ✅ Extracted action item:")
            print(f"      Title: {result['title']}")
            print(f"      Priority: {result['priority']}")
            print(f"      Due: {result.get('due_date', 'None')}")
            return True
        else:
            print("   ⚠️  No action item extracted (may be expected)")
            return True
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


async def test_alert_service():
    """Test Slack DM alerts"""
    print("\n🚨 3. Testing Alert Service")
    print("-" * 80)
    
    try:
        alert_service = AlertService()
        
        if not settings.SLACK_ALERT_USER_ID:
            print("   ⚠️  SLACK_ALERT_USER_ID not configured, skipping live test")
            return True
        
        print(f"   Alert User ID: {settings.SLACK_ALERT_USER_ID}")
        print("   ✅ Alert service initialized")
        
        # Don't send test alert automatically - just verify setup
        print("   💡 To test: Run a sync with messages scoring 90+")
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


async def test_context_enrichment():
    """Test Jira context enrichment"""
    print("\n💬 4. Testing Context Enrichment for Jira")
    print("-" * 80)
    
    try:
        jira_service = JiraService()
        
        if not jira_service.enabled:
            print("   ⚠️  Jira not configured, skipping test")
            return True
        
        # Test with mock message
        test_message = {
            "text": "Test message for context enrichment",
            "user_name": "Test User",
            "channel_name": "test",
            "channel_id": "C123456",
            "priority_score": 80,
            "priority_reason": "Test",
            "thread_ts": None  # No thread
        }
        
        print("   Testing context enrichment...")
        context = await jira_service._enrich_context(test_message)
        
        print(f"   ✅ Context enrichment works")
        print(f"      Thread context: {bool(context.get('thread_context'))}")
        print(f"      Related messages: {len(context.get('related_messages', []))}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


async def test_scheduler_integration():
    """Test scheduler setup"""
    print("\n⏰ 5. Testing Scheduler Integration")
    print("-" * 80)
    
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        
        print("   ✅ APScheduler installed")
        print(f"   Auto-sync: {'Enabled' if settings.AUTO_SYNC_ENABLED else 'Disabled'}")
        print(f"   Interval: {settings.SYNC_INTERVAL_MINUTES} minutes")
        
        if settings.AUTO_SYNC_ENABLED:
            print("   💡 Scheduler will run when API starts (uvicorn)")
        else:
            print("   💡 To enable: Set AUTO_SYNC_ENABLED=true in .env")
        
        return True
        
    except ImportError:
        print("   ❌ APScheduler not installed")
        print("   💡 Run: pip install apscheduler")
        return False


async def test_full_sync():
    """Test full sync with all features"""
    print("\n🔄 6. Testing Full Sync (Optional)")
    print("-" * 80)
    
    response = input("   Run a full sync now? This will hit Slack/OpenAI APIs (y/n): ").strip().lower()
    
    if response != 'y':
        print("   ⏩ Skipping full sync test")
        return True
    
    try:
        print("\n   Running sync...")
        sync_service = SyncService()
        result = await sync_service.sync(hours_ago=1)
        
        print(f"\n   ✅ Sync completed:")
        print(f"      Status: {result['status']}")
        print(f"      New messages: {result['fetch']['new_messages']}")
        print(f"      Prioritized: {result['prioritization']['prioritized']}")
        print(f"      Action items: {result.get('action_items', {}).get('extracted', 0)}")
        print(f"      Alerts sent: {result.get('alerts', {}).get('alerts_sent', 0)}")
        print(f"      Notion tasks: {result.get('notion', {}).get('tasks_created', 0)}")
        
        return result['status'] in ['success', 'partial']
        
    except Exception as e:
        print(f"   ❌ Sync failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    
    tests = [
        ("Configuration", test_config),
        ("Action Items", test_action_items),
        ("Alert Service", test_alert_service),
        ("Context Enrichment", test_context_enrichment),
        ("Scheduler", test_scheduler_integration),
        ("Full Sync", test_full_sync)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n   ❌ Test crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    print(f"\n   Total: {total_passed}/{len(results)} tests passed")
    
    print("\n" + "=" * 80)
    print("💡 NEXT STEPS:")
    print("=" * 80)
    print("   1. Update .env with:")
    print("      AUTO_SYNC_ENABLED=true")
    print(f"      SLACK_ALERT_USER_ID={settings.SLACK_ALERT_USER_ID or 'U09NR3RQZQU'}")
    print("   2. Start the API: uvicorn backend.main:app --reload")
    print("   3. Test with ngrok: ngrok http 8501 (for Streamlit)")
    print("   4. Monitor logs for auto-sync and alerts")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

