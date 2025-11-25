#!/usr/bin/env python3
"""
Test which simulation bots have which permissions
"""

import os
from slack_sdk import WebClient
from dotenv import load_dotenv

load_dotenv()

# Test all 3 simulation bots
bots = {
    "Manager Bot": os.getenv("BOT_MANAGER_TOKEN"),
    "Coworker Bot": os.getenv("BOT_COWORKER_TOKEN"),
    "Metrics Bot": os.getenv("BOT_METRICS_TOKEN"),
}

print("🔍 Testing Simulation Bot Permissions")
print("=" * 70)
print()

for bot_name, token in bots.items():
    print(f"Testing: {bot_name}")
    print("-" * 70)
    
    if not token:
        print(f"❌ Token not found in .env\n")
        continue
    
    client = WebClient(token=token)
    
    # Test 1: Can it post messages? (chat:write)
    try:
        # Test auth to see bot info
        auth_result = client.auth_test()
        print(f"✅ Bot Name: {auth_result['user']}")
        print(f"✅ Bot ID: {auth_result['user_id']}")
    except Exception as e:
        print(f"❌ Auth failed: {e}")
        continue
    
    # Test 2: Can it read channels? (channels:read)
    try:
        channels_result = client.conversations_list(limit=5)
        if channels_result['ok']:
            print(f"✅ Can read channels (found {len(channels_result['channels'])} channels)")
        else:
            print(f"❌ Cannot read channels: {channels_result.get('error')}")
    except Exception as e:
        error_msg = str(e)
        if 'missing_scope' in error_msg:
            print(f"❌ Cannot read channels: Missing scope")
        else:
            print(f"❌ Cannot read channels: {error_msg}")
    
    # Test 3: Can it read channel history? (channels:history)
    try:
        # Try to read from a known channel
        history_result = client.conversations_history(
            channel="C09P1KU5WMP",  # Your test channel
            limit=1
        )
        if history_result['ok']:
            print(f"✅ Can read channel history")
        else:
            print(f"❌ Cannot read history: {history_result.get('error')}")
    except Exception as e:
        error_msg = str(e)
        if 'missing_scope' in error_msg:
            print(f"❌ Cannot read history: Missing scope")
        elif 'not_in_channel' in error_msg:
            print(f"⚠️  Can read history but bot not in channel")
        else:
            print(f"❌ Cannot read history: {error_msg}")
    
    print()

print("=" * 70)
print("✅ Permission Test Complete")
print()
print("Summary:")
print("- For POSTING messages: Need chat:write")
print("- For READING channels: Need channels:read, groups:read, im:read, mpim:read")
print("- For READING history: Need channels:history, groups:history, im:history, mpim:history")

