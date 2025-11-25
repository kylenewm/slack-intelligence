#!/usr/bin/env python3
"""
Quick script to check your inbox from command line.
"""

import sys
import asyncio
import logging
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from backend.services.inbox_service import InboxService

logging.basicConfig(level=logging.WARNING)


async def main():
    """Check inbox and print results"""
    inbox = InboxService()
    
    print("\n" + "="*60)
    print("📬 YOUR SLACK INBOX")
    print("="*60)
    
    # Needs Response
    needs_response = await inbox.get_needs_response(hours_ago=24, limit=10)
    print(f"\n💬 NEEDS RESPONSE ({len(needs_response)} messages)")
    print("-" * 60)
    for msg in needs_response:
        print(f"[{msg['priority_score']}] #{msg['channel_name']} - {msg['user_name']}")
        print(f"    {msg['text'][:100]}...")
        print(f"    → {msg['priority_reason']}")
        print()
    
    # High Priority
    high_priority = await inbox.get_high_priority(hours_ago=24, limit=5)
    print(f"\n🔥 HIGH PRIORITY ({len(high_priority)} messages)")
    print("-" * 60)
    for msg in high_priority[:5]:
        print(f"[{msg['priority_score']}] #{msg['channel_name']} - {msg['user_name']}")
        print(f"    {msg['text'][:80]}...")
        print()
    
    # Stats
    stats = await inbox.get_stats()
    print(f"\n📊 STATS (Last 24h)")
    print("-" * 60)
    print(f"Total messages: {stats['total_messages']}")
    print(f"  - Needs response: {stats['by_category']['needs_response']}")
    print(f"  - High priority: {stats['by_category']['high_priority']}")
    print(f"  - FYI: {stats['by_category']['fyi']}")
    print(f"  - Low priority: {stats['by_category']['low_priority']}")
    print("="*60)
    print()


if __name__ == "__main__":
    asyncio.run(main())
