#!/usr/bin/env python3
"""
Generate realistic conversation threads for AI PM demo.
Creates natural back-and-forth discussions about real issues.

Uses the new persona bot tokens:
- BOT_SARAH_TOKEN - Sarah Chen (CTO)
- BOT_JORDAN_TOKEN - Jordan Patel (Engineering Manager)
- BOT_MARCUS_TOKEN - Marcus Johnson (Senior Engineer)
- BOT_ALEX_TOKEN - Alex Rivera (DevOps Engineer)
- BOT_METRICS_TOKEN - Metrics (Monitoring Bot)
"""

import os
import time
from slack_sdk import WebClient
from dotenv import load_dotenv

load_dotenv()

# Get API port from environment (default 8000)
API_PORT = int(os.getenv("API_PORT", "8000"))

# Bot clients representing different team members
bots = {
    "sarah": WebClient(token=os.getenv("BOT_SARAH_TOKEN")),      # CTO (VIP)
    "jordan": WebClient(token=os.getenv("BOT_JORDAN_TOKEN")),    # Eng Manager (VIP)
    "marcus": WebClient(token=os.getenv("BOT_MARCUS_TOKEN")),    # Senior Engineer
    "alex": WebClient(token=os.getenv("BOT_ALEX_TOKEN")),        # DevOps Engineer
    "metrics": WebClient(token=os.getenv("BOT_METRICS_TOKEN")),  # Monitoring Bot
}

# Your Slack user ID for @mentions
YOUR_USER_ID = os.getenv("YOUR_USER_ID", "U09NR3RQZQU")

# Channel IDs - set these in your .env
CHANNELS = {
    "incidents": os.getenv("CHANNEL_TEST_INCIDENTS"),
    "engineering": os.getenv("CHANNEL_TEST_ENGINEERING"),
    "product": os.getenv("CHANNEL_TEST_PRODUCT"),
    "watercooler": os.getenv("CHANNEL_TEST_WATERCOOLER"),
    "general": os.getenv("CHANNEL_GENERAL"),
}

# Realistic conversation scenarios
CONVERSATION_THREADS = [
    {
        "title": "Production Outage - API Down",
        "priority": "critical",
        "channel": "incidents",
        "messages": [
            {"bot": "metrics", "text": "🚨 ALERT: API response time > 10s. Error rate spiking to 45%. Affected: /api/v1/conversations endpoint", "delay": 1},
            {"bot": "alex", "text": "On it - checking the logs now. Seeing connection pool exhaustion on the primary DB", "delay": 3},
            {"bot": "marcus", "text": "I pushed a change to the query optimizer yesterday. Could be related?", "delay": 2},
            {"bot": "jordan", "text": f"<@{YOUR_USER_ID}> This is affecting 3 enterprise customers right now. What's our ETA on a fix? Should we rollback Marcus's change?", "delay": 2},
        ]
    },
    {
        "title": "Customer Escalation - Pricing Bug",
        "priority": "critical", 
        "channel": "incidents",
        "messages": [
            {"bot": "sarah", "text": "Just got off a call with Acme Corp's CEO. They're saying our system quoted wrong pricing on 5 deals this week. This is a P0.", "delay": 1},
            {"bot": "marcus", "text": "Looking at logs... found it. Edge case in the discount calculation when multiple promo codes are stacked", "delay": 3},
            {"bot": "sarah", "text": f"<@{YOUR_USER_ID}> I need you on a call with their CTO at 3pm to walk through the fix. Can you prepare a post-mortem doc?", "delay": 2},
        ]
    },
    {
        "title": "A/B Test Results Review",
        "priority": "high",
        "channel": "product",
        "messages": [
            {"bot": "metrics", "text": "📊 A/B Test Results: New onboarding flow\n• Variant B: +23% completion rate\n• Sample: 4,200 users\n• Statistical significance: 98%", "delay": 1},
            {"bot": "marcus", "text": "Nice! The simplified form really helped. Should we ship it?", "delay": 2},
            {"bot": "jordan", "text": "Before we ship - did we check mobile vs desktop breakdown? Last time mobile lagged behind", "delay": 2},
            {"bot": "sarah", "text": f"<@{YOUR_USER_ID}> Good results. Can you write up the go/no-go recommendation for tomorrow's product review?", "delay": 2},
        ]
    },
    {
        "title": "Architecture Discussion - Vector DB",
        "priority": "high",
        "channel": "engineering",
        "messages": [
            {"bot": "marcus", "text": "Been researching vector databases for the semantic search feature. Pinecone vs Weaviate vs pgvector - thoughts?", "delay": 1},
            {"bot": "alex", "text": "pgvector would be simplest since we're already on Postgres. But Pinecone has better performance at scale", "delay": 3},
            {"bot": "marcus", "text": "True. We're looking at ~10M vectors initially. Pinecone's free tier won't cut it", "delay": 2},
            {"bot": "jordan", "text": f"<@{YOUR_USER_ID}> This affects our Q4 roadmap and budget. Can you put together a comparison doc with cost projections?", "delay": 2},
        ]
    },
    {
        "title": "Sprint Planning",
        "priority": "medium",
        "channel": "engineering",
        "messages": [
            {"bot": "jordan", "text": "Morning team! Quick async standup - what's everyone working on this week?", "delay": 1},
            {"bot": "marcus", "text": "Finishing the conversation context persistence. Should be ready for QA by Wednesday", "delay": 3},
            {"bot": "alex", "text": "Setting up the new staging environment. Hit some IAM issues but should be resolved today", "delay": 2},
            {"bot": "jordan", "text": "Great progress. Reminder: stakeholder demo Friday at 2pm. Make sure staging is stable by then", "delay": 3},
        ]
    },
    {
        "title": "Casual Team Chat",
        "priority": "low",
        "channel": "watercooler",
        "messages": [
            {"bot": "marcus", "text": "Anyone tried that new ramen place on 5th? Thinking about lunch", "delay": 1},
            {"bot": "alex", "text": "The one with the spicy miso? It's 🔥 - get the extra chashu", "delay": 2},
            {"bot": "marcus", "text": "Also found a great article on LLM fine-tuning if anyone's interested. Will share in #engineering later", "delay": 3},
        ]
    },
]


def check_bot_tokens():
    """Verify all bot tokens are configured."""
    missing = []
    for name, client in bots.items():
        if not client.token:
            missing.append(name)
    
    if missing:
        print(f"❌ Missing bot tokens: {', '.join(missing)}")
        print("   Set these in your .env file:")
        for name in missing:
            env_var = f"BOT_{name.upper()}_TOKEN"
            print(f"   {env_var}=xoxb-...")
        return False
    return True


def check_channels():
    """Verify all channel IDs are configured."""
    missing = []
    for name, channel_id in CHANNELS.items():
        if not channel_id:
            missing.append(name)
    
    if missing:
        print(f"⚠️  Missing channel IDs: {', '.join(missing)}")
        print("   Set these in your .env file:")
        for name in missing:
            env_var = f"CHANNEL_TEST_{name.upper()}" if name != "general" else "CHANNEL_GENERAL"
            print(f"   {env_var}=C...")
        return False
    return True


def post_conversation_thread(thread_data):
    """Post a realistic conversation thread."""
    
    title = thread_data["title"]
    priority = thread_data["priority"]
    channel_name = thread_data["channel"]
    messages = thread_data["messages"]
    
    channel_id = CHANNELS.get(channel_name)
    if not channel_id:
        print(f"  ⚠️  Skipping - no channel ID for #{channel_name}")
        return False
    
    priority_emoji = {
        "critical": "🔴",
        "high": "🟡",
        "medium": "🟢",
        "low": "⚪"
    }[priority]
    
    print(f"\n{priority_emoji} {title} (#{channel_name})")
    print("-" * 60)
    
    for msg in messages:
        bot_name = msg["bot"]
        text = msg["text"]
        delay = msg["delay"]
        
        try:
            bot = bots.get(bot_name)
            if not bot or not bot.token:
                print(f"  ⚠️  Bot '{bot_name}' not configured, skipping")
                continue
                
            result = bot.chat_postMessage(
                channel=channel_id,
                text=text
            )
            
            print(f"  {bot_name}: {text[:70]}...")
            time.sleep(delay)
            
        except Exception as e:
            print(f"  ❌ Error ({bot_name}): {e}")
    
    return True


def main():
    print("🎭 Realistic AI PM Conversation Generator")
    print("=" * 60)
    print("Team: Sarah (CTO), Jordan (Manager), Marcus (Engineer), Alex (DevOps)")
    print()
    
    # Check configuration
    if not check_bot_tokens():
        print("\n❌ Cannot proceed without bot tokens")
        return
    
    check_channels()  # Warning only, continue anyway
    
    print("\nGenerating natural conversation threads...")
    
    posted = 0
    for thread in CONVERSATION_THREADS:
        if post_conversation_thread(thread):
            posted += 1
        time.sleep(2)  # Pause between conversation threads
    
    print("\n" + "=" * 60)
    print(f"🎉 Posted {posted} conversation threads!")
    print()
    print("📋 Scenarios Created:")
    print("  🔴 2 critical (production outage, customer escalation)")
    print("  🟡 2 high priority (A/B test, architecture decision)")  
    print("  🟢 1 medium priority (sprint planning)")
    print("  ⚪ 1 low priority (casual chat)")
    print()
    print("⏰ Next Steps:")
    print("1. Wait ~30 seconds for Slack to process")
    print(f"2. Sync: python scripts/sync_once.py")
    print(f"3. View results: python scripts/view_simulation_results.py")
    print(f"4. Or open Streamlit: http://localhost:8502")


if __name__ == "__main__":
    main()
