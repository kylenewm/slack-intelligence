#!/usr/bin/env python3
"""
Test Notion integration with simulated Slack data.
This allows testing before connecting to production Slack.
"""

import sys
import asyncio
import logging
from pathlib import Path

backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from integrations.notion_service import NotionSyncService, NotionTaskExtractor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Test messages (simulated)
SAMPLE_MESSAGES = [
    {
        'text': 'URGENT: Production database is down! Need immediate help',
        'user_name': 'Sarah Chen',
        'channel_name': 'critical-alerts',
        'priority_score': 95
    },
    {
        'text': 'Please review the Q4 strategy doc and provide feedback by EOD tomorrow',
        'user_name': 'John Manager',
        'channel_name': 'strategic-planning',
        'priority_score': 85
    },
    {
        'text': 'New feature request: Add dark mode support. Here are the wireframes...',
        'user_name': 'Design Team',
        'channel_name': 'product',
        'priority_score': 72
    },
    {
        'text': 'Happy Friday everyone! 🎉 Let\'s celebrate the launch!',
        'user_name': 'CEO',
        'channel_name': 'general',
        'priority_score': 35
    },
    {
        'text': 'Action items from today\'s standup:\n1. Fix API timeout issue\n2. Update documentation\n3. Review PRs',
        'user_name': 'Tech Lead',
        'channel_name': 'engineering',
        'priority_score': 80
    }
]


def test_task_extraction():
    """Test task extraction from messages"""
    print("\n" + "=" * 60)
    print("🔍 Testing Task Extraction")
    print("=" * 60)
    
    extractor = NotionTaskExtractor()
    
    for i, msg in enumerate(SAMPLE_MESSAGES, 1):
        print(f"\n📨 Message {i}:")
        print(f"   Text: {msg['text'][:60]}...")
        print(f"   Priority: {msg['priority_score']}")
        
        task = extractor.extract_task_from_message(msg)
        
        if task:
            print(f"   ✅ Task extracted:")
            print(f"      Title: {task['title']}")
            print(f"      Description preview: {task['description'][:80]}...")
        else:
            print(f"   ⬇️  No task (low priority)")


async def test_notion_client():
    """Test Notion client configuration"""
    print("\n" + "=" * 60)
    print("🧪 Testing Notion Integration Setup")
    print("=" * 60)
    
    from backend.config import settings
    
    print(f"\n📋 Notion Configuration Status:")
    print(f"   API Key set: {'✅' if settings.NOTION_API_KEY else '❌'}")
    print(f"   Database ID set: {'✅' if settings.NOTION_DATABASE_ID else '❌'}")
    print(f"   Sync enabled: {'✅' if settings.NOTION_SYNC_ENABLED else '⚠️'}")
    print(f"   Min priority score: {settings.NOTION_MIN_PRIORITY_SCORE}")
    
    if not settings.NOTION_API_KEY or not settings.NOTION_DATABASE_ID:
        print("\n⚠️  To enable Notion integration, add to .env:")
        print("   NOTION_API_KEY=ntn_...(from https://notion.so/my-integrations)")
        print("   NOTION_DATABASE_ID=... (copy from your Notion database URL)")
        print("   NOTION_SYNC_ENABLED=true")
        return False
    
    return True


async def test_full_sync():
    """Test full Notion sync with sample data"""
    print("\n" + "=" * 60)
    print("🚀 Testing Full Notion Sync")
    print("=" * 60)
    
    from backend.config import settings
    
    # Create sync service
    service = NotionSyncService(
        api_key=settings.NOTION_API_KEY,
        database_id=settings.NOTION_DATABASE_ID
    )
    
    if not service.enabled:
        print("\n⚠️  Notion integration not configured")
        print("\nTo test with real Notion database:")
        print("1. Go to https://notion.so/my-integrations")
        print("2. Create integration and get API key")
        print("3. Create a Notion database with columns:")
        print("   - Name (Title)")
        print("   - Description (Rich text)")
        print("   - Priority (Select: Critical, High, Medium, Low)")
        print("   - Source (Select: Slack)")
        print("   - Status (Select: Not Started, In Progress, Done)")
        print("4. Add to .env and restart")
        return
    
    print(f"\n📤 Syncing {len(SAMPLE_MESSAGES)} sample messages...")
    
    result = await service.sync_messages_to_notion(SAMPLE_MESSAGES)
    
    print(f"\n✅ Sync Results:")
    print(f"   Status: {result['status']}")
    print(f"   Tasks created: {result['tasks_created']}")
    print(f"   Tasks skipped: {result['tasks_skipped']}")
    print(f"   Errors: {result['errors']}")
    
    if result['tasks_created'] > 0:
        print(f"\n🎉 Successfully synced {result['tasks_created']} tasks to Notion!")


async def main():
    """Run all tests"""
    print("\n🧪 Notion Integration Test Suite")
    print("=" * 60)
    
    # Test 1: Task extraction
    test_task_extraction()
    
    # Test 2: Configuration check
    await test_notion_client()
    
    # Test 3: Full sync (if configured)
    await test_full_sync()
    
    print("\n" + "=" * 60)
    print("✅ Test suite complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
