#!/usr/bin/env python3
"""
Quick test to verify simulation bots are no longer filtered out
"""

import asyncio
import sys
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

from backend.config import settings
from backend.ingestion.slack_ingester import SlackIngester

async def test_bot_filtering():
    print("=" * 80)
    print("🤖 TESTING BOT MESSAGE FILTERING")
    print("=" * 80)
    print()
    
    print("Configuration:")
    print(f"  Slack Bot Token: {'✅ Set' if settings.SLACK_BOT_TOKEN else '❌ Not Set'}")
    print()
    
    print("Expected behavior:")
    print("  ✅ KEEP: Manager Bot (U09N761B1RD)")
    print("  ✅ KEEP: Metrics Bot (U09NG7YLB2P)")
    print("  ✅ KEEP: Coworker Bot (U09P1GUPDH7)")
    print("  ❌ SKIP: Other bots (bot_id present)")
    print()
    
    print("Fetching recent messages from Slack...")
    ingester = SlackIngester()
    result = await ingester.sync_channels(hours_ago=24)
    
    print()
    print("=" * 80)
    print("SYNC RESULTS")
    print("=" * 80)
    
    stats = result['stats']
    print(f"Messages fetched: {stats['messages_fetched']}")
    print(f"New messages: {stats['new_messages']}")
    print(f"Channels synced: {stats['channels_synced']}")
    
    # Check for bot messages in database
    from backend.database.cache_service import CacheService
    cache = CacheService()
    
    # Get recent messages
    from backend.database.models import SlackMessage
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    messages = session.query(SlackMessage).order_by(SlackMessage.timestamp.desc()).limit(100).all()
    
    print()
    print("=" * 80)
    print("CHECKING FOR SIMULATION BOT MESSAGES")
    print("=" * 80)
    
    simulation_bot_ids = ['U09N761B1RD', 'U09NG7YLB2P', 'U09P1GUPDH7']
    simulation_bot_names = {
        'U09N761B1RD': 'Manager Bot',
        'U09NG7YLB2P': 'Metrics Bot',
        'U09P1GUPDH7': 'Coworker Bot'
    }
    
    bot_message_counts = {bot_id: 0 for bot_id in simulation_bot_ids}
    
    for msg in messages:
        if msg.user_id in simulation_bot_ids:
            bot_message_counts[msg.user_id] += 1
    
    print()
    for bot_id, count in bot_message_counts.items():
        bot_name = simulation_bot_names[bot_id]
        status = "✅" if count > 0 else "⚠️"
        print(f"{status} {bot_name}: {count} messages found")
    
    print()
    print("=" * 80)
    if sum(bot_message_counts.values()) > 0:
        print("✅ SUCCESS: Simulation bot messages are being kept!")
    else:
        print("⚠️  WARNING: No simulation bot messages found")
        print("   This could mean:")
        print("   - No messages from simulation bots in last 24 hours")
        print("   - Bots haven't posted yet")
        print("   💡 Generate some test messages and sync again")
    print("=" * 80)
    
    session.close()

if __name__ == "__main__":
    asyncio.run(test_bot_filtering())

