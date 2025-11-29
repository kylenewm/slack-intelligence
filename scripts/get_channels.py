#!/usr/bin/env python3
"""
Get channel IDs from your Slack workspace using the main bot.
"""

import os
from slack_sdk import WebClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_channels():
    """Get list of channels the main bot can access"""
    
    # Use the main Slack Intelligence bot (has proper scopes)
    # Try personal token first, fallback to default
    token = os.getenv("SLACK_BOT_TOKEN_PERSONAL") or os.getenv("SLACK_BOT_TOKEN")
    client = WebClient(token=token)
    
    try:
        result = client.conversations_list(
            types="public_channel,private_channel",
            exclude_archived=True,
            limit=100
        )
        
        channels = result.get('channels', [])
        
        print("📋 Available Channels:")
        print("=" * 50)
        
        for ch in channels:
            if ch.get('is_member', False):
                print(f"✅ #{ch['name']} - {ch['id']}")
            else:
                print(f"❌ #{ch['name']} - {ch['id']} (not a member)")
        
        # Get joined channels only
        joined_channels = [ch['id'] for ch in channels if ch.get('is_member', False)]
        
        print(f"\n🎯 You can use these {len(joined_channels)} channels for testing:")
        for ch_id in joined_channels[:5]:  # Show first 5
            print(f"   {ch_id}")
            
        return joined_channels
        
    except Exception as e:
        print(f"❌ Error getting channels: {e}")
        return []

if __name__ == "__main__":
    get_channels()
