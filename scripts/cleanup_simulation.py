#!/usr/bin/env python3
"""
Cleanup Simulation Messages

Removes simulation messages from:
1. Database (messages with [SIM] prefix or sim_ message ID)
2. Optionally from Slack channels (requires chat:write scope)

Usage:
    python scripts/cleanup_simulation.py              # Cleanup database only
    python scripts/cleanup_simulation.py --slack      # Also attempt Slack deletion
    python scripts/cleanup_simulation.py --dry-run    # Preview what would be deleted
"""

import os
import sys
import argparse
from datetime import datetime, timedelta

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from backend.database.db import SessionLocal
from backend.database.models import SlackMessage


def cleanup_database(dry_run: bool = False) -> int:
    """Remove simulation messages from database."""
    print("\n🗄️  Database Cleanup")
    print("-" * 50)
    
    db = SessionLocal()
    
    try:
        # Find simulation messages
        sim_messages = db.query(SlackMessage).filter(
            (SlackMessage.text.contains("[SIM]")) | 
            (SlackMessage.message_id.like("sim_%"))
        ).all()
        
        if not sim_messages:
            print("   No simulation messages found in database")
            return 0
        
        print(f"   Found {len(sim_messages)} simulation messages")
        
        # Show preview
        for msg in sim_messages[:5]:
            text = (msg.text or "")[:50].replace("[SIM] ", "")
            print(f"   - [{msg.user_name}] {text}...")
        
        if len(sim_messages) > 5:
            print(f"   ... and {len(sim_messages) - 5} more")
        
        if dry_run:
            print("\n   [DRY RUN] Would delete these messages")
            return len(sim_messages)
        
        # Delete
        count = 0
        for msg in sim_messages:
            db.delete(msg)
            count += 1
        
        db.commit()
        print(f"\n   ✅ Deleted {count} messages from database")
        return count
        
    finally:
        db.close()


def cleanup_slack(dry_run: bool = False) -> int:
    """Attempt to remove simulation messages from Slack channels."""
    print("\n💬 Slack Cleanup")
    print("-" * 50)
    
    # Channel IDs from environment
    channels = {
        "incidents": os.getenv("CHANNEL_INCIDENTS"),
        "engineering": os.getenv("CHANNEL_ENGINEERING"),
        "product": os.getenv("CHANNEL_PRODUCT"),
        "watercooler": os.getenv("CHANNEL_WATERCOOLER"),
        "general": os.getenv("CHANNEL_GENERAL"),
    }
    
    # Bot tokens for deletion (each bot can only delete its own messages)
    bots = {
        "Sarah Chen": os.getenv("BOT_SARAH_TOKEN"),
        "Jordan Patel": os.getenv("BOT_JORDAN_TOKEN"),
        "Marcus Johnson": os.getenv("BOT_MARCUS_TOKEN"),
        "Alex Rivera": os.getenv("BOT_ALEX_TOKEN"),
        "Metrics": os.getenv("BOT_METRICS_TOKEN"),
    }
    
    # Use main bot to read channels (try personal token first)
    main_token = os.getenv("SLACK_BOT_TOKEN_PERSONAL") or os.getenv("SLACK_BOT_TOKEN")
    if not main_token:
        print("   ❌ SLACK_BOT_TOKEN not set, cannot read channels")
        return 0
    
    main_bot = WebClient(token=main_token)
    
    total_found = 0
    total_deleted = 0
    
    for channel_name, channel_id in channels.items():
        if not channel_id:
            continue
        
        print(f"\n   Checking #{channel_name}...")
        
        try:
            # Get recent messages
            result = main_bot.conversations_history(
                channel=channel_id,
                limit=200
            )
            
            messages = result.get("messages", [])
            sim_messages = [m for m in messages if "[SIM]" in m.get("text", "")]
            
            if not sim_messages:
                print(f"      No simulation messages")
                continue
            
            print(f"      Found {len(sim_messages)} simulation messages")
            total_found += len(sim_messages)
            
            if dry_run:
                for msg in sim_messages[:3]:
                    text = msg.get("text", "")[:40].replace("[SIM] ", "")
                    print(f"      - Would delete: {text}...")
                continue
            
            # Try to delete each message
            # Note: Can only delete messages from bots we control
            for msg in sim_messages:
                ts = msg.get("ts")
                bot_id = msg.get("bot_id")
                
                # Try each bot token
                deleted = False
                for bot_name, token in bots.items():
                    if not token:
                        continue
                    try:
                        bot = WebClient(token=token)
                        bot.chat_delete(channel=channel_id, ts=ts)
                        print(f"      ✓ Deleted message via {bot_name}")
                        total_deleted += 1
                        deleted = True
                        break
                    except SlackApiError:
                        continue
                
                if not deleted:
                    print(f"      ⚠️  Could not delete: {msg.get('text', '')[:30]}...")
                    
        except SlackApiError as e:
            print(f"      ❌ Error: {e.response['error']}")
    
    print(f"\n   Found: {total_found} | Deleted: {total_deleted}")
    return total_deleted


def main():
    parser = argparse.ArgumentParser(description="Cleanup Simulation Messages")
    parser.add_argument("--slack", "-s", action="store_true", help="Also cleanup Slack channels")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Preview without deleting")
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("🧹 SIMULATION CLEANUP")
    print("=" * 60)
    
    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No actual deletions\n")
    
    # Database cleanup
    db_count = cleanup_database(dry_run=args.dry_run)
    
    # Slack cleanup (optional)
    slack_count = 0
    if args.slack:
        slack_count = cleanup_slack(dry_run=args.dry_run)
    else:
        print("\n   💡 Run with --slack to also cleanup Slack channels")
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ CLEANUP COMPLETE")
    print("=" * 60)
    
    if args.dry_run:
        print(f"   Would delete: {db_count} DB messages, {slack_count} Slack messages")
    else:
        print(f"   Deleted: {db_count} DB messages, {slack_count} Slack messages")


if __name__ == "__main__":
    main()

