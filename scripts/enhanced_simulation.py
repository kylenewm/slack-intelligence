#!/usr/bin/env python3
"""
Enhanced realistic conversation generator with Slack notifications.
Posts conversations and sends you a DM summary in Slack!
"""

import os
import time
from slack_sdk import WebClient
from dotenv import load_dotenv

load_dotenv()

# Get API port from environment (default 8000)
API_PORT = int(os.getenv("API_PORT", "8000"))

# Bot clients
bots = {
    "manager": WebClient(token=os.getenv("BOT_MANAGER_TOKEN")),
    "engineer": WebClient(token=os.getenv("BOT_COWORKER_TOKEN")),
    "metrics": WebClient(token=os.getenv("BOT_METRICS_TOKEN")),
}

# Main intelligence bot for sending DMs
main_bot = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

YOUR_USER_ID = os.getenv("YOUR_USER_ID", "U09NR3RQZQU")
CHANNEL_ID = "C09P1KU5WMP"

# Fresh realistic conversations with clear categories
CONVERSATIONS = {
    "🔴 CRITICAL": [
        {
            "title": "Production Outage",
            "messages": [
                {"bot": "engineer", "text": "🚨 Production alert: Sales bot API returning 503s", "delay": 1},
                {"bot": "engineer", "text": "Error rate jumped from 0.1% to 45% in last 5 minutes. Database connections timing out", "delay": 2},
                {"bot": "manager", "text": f"<@{YOUR_USER_ID}> We have 8 enterprise customers affected. Need your call NOW - do we failover to backup or investigate?", "delay": 2},
            ]
        },
        {
            "title": "Customer Emergency",
            "messages": [
                {"bot": "manager", "text": "Just got escalated by our biggest client (Acme - $2M/yr)", "delay": 1},
                {"bot": "manager", "text": f"<@{YOUR_USER_ID}> Their CEO is asking why our bot recommended wrong products to 10+ leads. Need you on a call in 15 minutes", "delay": 2},
            ]
        },
    ],
    
    "🟡 HIGH PRIORITY": [
        {
            "title": "Performance Degradation",
            "messages": [
                {"bot": "engineer", "text": "Intent detection latency increased to 3.2s (was 800ms yesterday)", "delay": 1},
                {"bot": "metrics", "text": "Seeing 23% drop in conversation completion rate as a result", "delay": 2},
                {"bot": "manager", "text": f"<@{YOUR_USER_ID}> Sales team is complaining. Thoughts on quick wins vs long-term fix?", "delay": 2},
            ]
        },
        {
            "title": "Feature Request from Key Customer",
            "messages": [
                {"bot": "manager", "text": "Salesforce integration request from TechCorp (they're considering enterprise plan)", "delay": 1},
                {"bot": "engineer", "text": "We have the API built, just need to expose it in the bot conversation flow", "delay": 2},
                {"bot": "manager", "text": "Estimated 2 days of work. Could close $500K deal if we ship by Friday", "delay": 2},
            ]
        },
    ],
    
    "🟢 MEDIUM PRIORITY": [
        {
            "title": "Weekly Metrics Review",
            "messages": [
                {"bot": "metrics", "text": "Week 43 metrics: 12,300 conversations (+8%), 92% satisfaction (+3%), 1.1s avg response time", "delay": 1},
                {"bot": "engineer", "text": "Nice improvement on satisfaction! The new context handling is working", "delay": 2},
                {"bot": "manager", "text": "Great work team. Let's discuss optimization priorities in Friday's standup", "delay": 2},
            ]
        },
    ],
    
    "⚪ LOW PRIORITY": [
        {
            "title": "Team Social",
            "messages": [
                {"bot": "engineer", "text": "Anyone up for coffee? There's a new place on 2nd Ave", "delay": 1},
                {"bot": "metrics", "text": "I'm in! 3pm work for everyone?", "delay": 2},
            ]
        },
        {
            "title": "Automated Report",
            "messages": [
                {"bot": "metrics", "text": "🤖 Automated Daily Report: 847 conversations, 88% satisfaction, 1.2s avg response", "delay": 1},
            ]
        },
    ],
}

def post_conversations():
    """Post all conversation threads"""
    
    print("🎭 Enhanced Realistic Conversation Generator")
    print("=" * 60)
    print("Generating fresh, realistic AI PM conversations...")
    print()
    
    stats = {
        "🔴 CRITICAL": 0,
        "🟡 HIGH PRIORITY": 0,
        "🟢 MEDIUM PRIORITY": 0,
        "⚪ LOW PRIORITY": 0,
    }
    
    all_threads = []
    
    for category, threads in CONVERSATIONS.items():
        print(f"\n{category}")
        print("-" * 60)
        
        for thread in threads:
            thread_title = thread["title"]
            messages = thread["messages"]
            
            print(f"  📝 {thread_title}")
            
            thread_messages = []
            
            for msg in messages:
                bot_name = msg["bot"]
                text = msg["text"]
                delay = msg["delay"]
                
                try:
                    bot = bots[bot_name]
                    result = bot.chat_postMessage(
                        channel=CHANNEL_ID,
                        text=text
                    )
                    
                    print(f"     {bot_name}: {text[:60]}...")
                    thread_messages.append(text)
                    time.sleep(delay)
                    
                except Exception as e:
                    print(f"     ❌ Error: {e}")
            
            stats[category] += 1
            all_threads.append({
                "category": category,
                "title": thread_title,
                "messages": thread_messages
            })
            
            time.sleep(1)  # Pause between threads
    
    return stats, all_threads

def send_slack_dm_notification(stats, threads):
    """Send a DM to the user in Slack with the simulation summary"""
    
    print("\n" + "=" * 60)
    print("📬 Sending Slack DM notification...")
    
    # Build the message
    message_lines = [
        "🤖 *Slack Intelligence Test Simulation*",
        "",
        "I just generated realistic AI PM conversations for testing. Here's what was posted:",
        "",
        "*Summary by Category:*",
    ]
    
    for category, count in stats.items():
        message_lines.append(f"{category}: {count} conversation thread(s)")
    
    message_lines.extend([
        "",
        "*What to expect:*",
        "• You should get audio notifications for 🔴 CRITICAL messages within 1 minute",
        f"• Check your smart inbox: http://localhost:{API_PORT}/api/slack/inbox?view=needs_response",
        "• The system will prioritize @mentions and urgent keywords",
        "",
        "_These are realistic test conversations between Manager Bot, Engineer Bot, and Metrics Bot._"
    ])
    
    message = "\n".join(message_lines)
    
    try:
        result = main_bot.chat_postMessage(
            channel=YOUR_USER_ID,  # DM to you
            text=message
        )
        print("✅ Sent Slack DM notification to you!")
        return True
    except Exception as e:
        print(f"❌ Error sending Slack DM: {e}")
        print(f"   (Your Slack Intelligence bot might need 'chat:write' and 'im:write' permissions)")
        return False

def main():
    """Main function"""
    
    # Post conversations
    stats, threads = post_conversations()
    
    # Send Slack DM
    print("\n" + "=" * 60)
    send_slack_dm_notification(stats, threads)
    
    # Summary
    print("\n" + "=" * 60)
    print("🎉 Fresh realistic conversations posted!")
    print()
    print("📊 Summary:")
    for category, count in stats.items():
        print(f"   {category}: {count} thread(s)")
    
    total = sum(stats.values())
    print(f"\n   Total: {total} conversation threads")
    print()
    print("⏰ Next Steps:")
    print("1. Check your Slack DMs for the notification")
    print("2. Wait ~1 minute for audio notifications on critical messages")
    print(f"3. Run: curl -X POST 'http://localhost:{API_PORT}/api/slack/sync?hours_ago=1'")
    print(f"4. Check: curl -s 'http://localhost:{API_PORT}/api/slack/inbox?view=needs_response'")
    print()

if __name__ == "__main__":
    main()

