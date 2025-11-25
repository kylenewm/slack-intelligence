#!/usr/bin/env python3
"""
Test Slack DM alerts with existing high-priority messages
"""

import asyncio
import sys
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

from backend.services.alert_service import AlertService
from backend.database.cache_service import CacheService

async def test_alerts():
    print("=" * 80)
    print("🚨 TESTING SLACK DM ALERTS")
    print("=" * 80)
    print()
    
    cache = CacheService()
    alert_service = AlertService()
    
    # Get high-priority messages (score >= 90)
    messages = cache.get_messages_by_score_range(
        min_score=90,
        max_score=100,
        hours_ago=24,
        limit=10
    )
    
    print(f"Found {len(messages)} messages with score >= 90")
    print()
    
    if not messages:
        print("⚠️  No messages with score >= 90 found")
        print("💡 Try syncing first or wait for new high-priority messages")
        return
    
    print("Messages that will trigger alerts:")
    for i, msg in enumerate(messages, 1):
        print(f"{i}. [{msg['priority_score']}] {msg['user_name']} in #{msg['channel_name']}")
        print(f"   {msg['text'][:60]}...")
        print()
    
    print("=" * 80)
    print("Sending alerts...")
    print("=" * 80)
    print()
    
    result = await alert_service.send_critical_alerts(messages)
    
    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Status: {result['status']}")
    print(f"Alerts sent: {result['alerts_sent']}")
    
    if result.get('errors'):
        print(f"Errors: {len(result['errors'])}")
        for error in result['errors'][:3]:
            print(f"  - {error}")
    
    print()
    print("=" * 80)
    if result['alerts_sent'] > 0:
        print("✅ SUCCESS! Check your Slack DMs")
        print(f"You should have {result['alerts_sent']} new DM(s) from Slack Intelligence bot")
    else:
        print("❌ No alerts sent - check errors above")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_alerts())

