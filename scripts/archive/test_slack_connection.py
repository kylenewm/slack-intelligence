#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from slack_sdk import WebClient

load_dotenv()

bot_token = os.getenv("SLACK_BOT_TOKEN")
client = WebClient(token=bot_token)

print("🔍 Testing Slack Connection...")
print("=" * 50)

try:
    # Test auth
    auth = client.auth_test()
    print(f"✅ Bot connected!")
    print(f"   Bot ID: {auth['user_id']}")
    print(f"   Bot Name: {auth['user']}")
    print(f"   Team: {auth['team']}")
    print()
    
    # List channels
    print("📋 Channels bot has access to:")
    result = client.conversations_list(types="public_channel,private_channel")
    channels = result['channels']
    
    if not channels:
        print("   ❌ No channels found!")
        print("\n   This means the bot hasn't been invited to any channels yet.")
        print("\n   To fix:")
        print("   1. Go to any channel in Slack")
        print(f"   2. Type: /invite @{auth['user']}")
        print("   3. Or right-click channel → Add apps → Select your bot")
    else:
        for channel in channels:
            member_status = "✅ MEMBER" if channel['is_member'] else "❌ Not member"
            print(f"   {member_status} - #{channel['name']} (ID: {channel['id']})")
    
except Exception as e:
    print(f"❌ Error: {e}")
    
print("=" * 50)
