#!/usr/bin/env python3
"""
Generate realistic conversation threads for AI PM demo.
Creates natural back-and-forth discussions about real issues.
"""

import os
import time
from slack_sdk import WebClient
from dotenv import load_dotenv

load_dotenv()

# Get API port from environment (default 8000)
API_PORT = int(os.getenv("API_PORT", "8000"))

# Bot clients representing different people
bots = {
    "manager": WebClient(token=os.getenv("BOT_MANAGER_TOKEN")),
    "engineer": WebClient(token=os.getenv("BOT_COWORKER_TOKEN")),
    "metrics": WebClient(token=os.getenv("BOT_METRICS_TOKEN")),
}

YOUR_USER_ID = os.getenv("YOUR_USER_ID", "U09NR3RQZQU")
CHANNEL_ID = "C09P1KU5WMP"

# Realistic conversation scenarios
CONVERSATION_THREADS = [
    {
        "title": "Production Issue - Sales Bot Down",
        "priority": "critical",
        "messages": [
            {"bot": "engineer", "text": "Hey team, anyone else seeing 500 errors on the sales bot API?", "delay": 1},
            {"bot": "engineer", "text": "Just checked - intent detection service is timing out. Response times jumped from 800ms to 12s", "delay": 3},
            {"bot": "manager", "text": f"<@{YOUR_USER_ID}> This is blocking 5 enterprise customer conversations right now. Need your call - do we rollback to v2.3 or try a hotfix?", "delay": 2},
        ]
    },
    {
        "title": "Customer Escalation",
        "priority": "critical",
        "messages": [
            {"bot": "manager", "text": "Just got off a call with Acme Corp. Their sales team is saying our bot gave wrong pricing on 3 deals this week", "delay": 1},
            {"bot": "engineer", "text": "Looking at logs now... seeing some edge cases where the pricing API returned null and bot didn't handle it gracefully", "delay": 3},
            {"bot": "manager", "text": f"<@{YOUR_USER_ID}> Customer wants to know our fix timeline. Can you jump on a call at 3pm to discuss the technical details with their CTO?", "delay": 2},
        ]
    },
    {
        "title": "A/B Test Results Discussion",
        "priority": "high",
        "messages": [
            {"bot": "metrics", "text": "A/B test results are in for the new conversation flow", "delay": 1},
            {"bot": "engineer", "text": "Nice! What are the numbers?", "delay": 2},
            {"bot": "metrics", "text": "Variant B shows 18% improvement in lead quality, but 8% drop in completion rate. Sample size: 2,400 conversations", "delay": 2},
            {"bot": "engineer", "text": "Interesting trade-off. The drop in completion might be because we're asking more qualifying questions", "delay": 3},
            {"bot": "manager", "text": f"<@{YOUR_USER_ID}> Need your product decision here - do we optimize for quality or quantity? Sales team is pushing for the quality improvement", "delay": 2},
        ]
    },
    {
        "title": "Technical Architecture Debate",
        "priority": "high",
        "messages": [
            {"bot": "engineer", "text": "Been thinking about the intent detection accuracy issues. What if we switch from single-model to ensemble approach?", "delay": 1},
            {"bot": "engineer", "text": "Could run 3 models in parallel (BERT, GPT-4-mini, our custom model) and use weighted voting", "delay": 3},
            {"bot": "manager", "text": "What's the latency impact? We're already pushing our 2s response time budget", "delay": 2},
            {"bot": "engineer", "text": "Good point. Parallel requests would keep latency similar, but costs go up 3x. Could cache common intents though", "delay": 3},
            {"bot": "manager", "text": f"<@{YOUR_USER_ID}> This affects our Q4 roadmap. Thoughts on accuracy vs cost tradeoff here?", "delay": 2},
        ]
    },
    {
        "title": "Weekly Standup Discussion",
        "priority": "medium",
        "messages": [
            {"bot": "manager", "text": "Morning team! Quick async standup for this week", "delay": 1},
            {"bot": "engineer", "text": "Finishing up the conversation context persistence feature. Should be ready for QA tomorrow", "delay": 3},
            {"bot": "metrics", "text": "Last week: 8,400 conversations, 91% satisfaction rate (up from 89%), avg response time 1.2s", "delay": 2},
            {"bot": "manager", "text": "Great progress. Reminder: demo for stakeholders Friday at 2pm. Make sure the staging env is stable", "delay": 3},
        ]
    },
    {
        "title": "Casual Team Chat",
        "priority": "low",
        "messages": [
            {"bot": "engineer", "text": "Anyone grab lunch yet? Thinking about the new ramen place", "delay": 1},
            {"bot": "engineer", "text": "Also found a good blog post on LLM prompt engineering if anyone's interested", "delay": 3},
            {"bot": "metrics", "text": "I'm in for ramen! 12:30?", "delay": 2},
        ]
    },
]

def post_conversation_thread(thread_data):
    """Post a realistic conversation thread"""
    
    title = thread_data["title"]
    priority = thread_data["priority"]
    messages = thread_data["messages"]
    
    priority_emoji = {
        "critical": "🔴",
        "high": "🟡",
        "medium": "🟢",
        "low": "⚪"
    }[priority]
    
    print(f"\n{priority_emoji} {title}")
    print("-" * 60)
    
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
            
            print(f"  {bot_name}: {text[:70]}...")
            time.sleep(delay)
            
        except Exception as e:
            print(f"  ❌ Error: {e}")

def main():
    print("🎭 Realistic AI PM Conversation Generator")
    print("=" * 60)
    print("Generating natural conversation threads for demo...")
    print()
    
    for thread in CONVERSATION_THREADS:
        post_conversation_thread(thread)
        time.sleep(2)  # Pause between conversation threads
    
    print("\n" + "=" * 60)
    print("🎉 Posted realistic conversation threads!")
    print()
    print("📋 Scenarios Created:")
    print("  🔴 2 critical conversations (production issue, customer escalation)")
    print("  🟡 2 high priority (A/B test, architecture debate)")  
    print("  🟢 1 medium priority (weekly standup)")
    print("  ⚪1 low priority (casual team chat)")
    print()
    print("⏰ Next Steps:")
    print("1. Wait ~1 minute for notifications")
    print(f"2. Run: curl -X POST 'http://localhost:{API_PORT}/api/slack/sync?hours_ago=1'")
    print(f"3. Check: curl -s 'http://localhost:{API_PORT}/api/slack/inbox?view=all'")

if __name__ == "__main__":
    main()

