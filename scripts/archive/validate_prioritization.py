#!/usr/bin/env python3
"""
Validate that the AI prioritization is working correctly for generated test messages.
"""

import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API port from environment (default 8000)
API_PORT = int(os.getenv("API_PORT", "8000"))
API_BASE = f"http://localhost:{API_PORT}"

def get_inbox_data():
    """Get all messages from the inbox API"""
    try:
        response = requests.get(f"{API_BASE}/api/slack/inbox?view=all&limit=100")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching inbox data: {e}")
        return None

def analyze_prioritization(data):
    """Analyze the prioritization results"""
    
    if not data or not data.get('messages'):
        print("❌ No messages found")
        return
    
    messages = data['messages']
    total = len(messages)
    
    print(f"📊 Prioritization Analysis ({total} messages)")
    print("=" * 60)
    
    # Categorize by priority score
    critical = [m for m in messages if m['priority_score'] >= 90]
    high = [m for m in messages if 70 <= m['priority_score'] < 90]
    medium = [m for m in messages if 50 <= m['priority_score'] < 70]
    low = [m for m in messages if m['priority_score'] < 50]
    
    print(f"🔴 Critical (90+): {len(critical)} messages")
    for msg in critical[:3]:  # Show top 3
        print(f"   [{msg['priority_score']}] {msg['text'][:60]}...")
        print(f"   → {msg['priority_reason']}")
        print()
    
    print(f"🟡 High (70-89): {len(high)} messages")
    for msg in high[:3]:
        print(f"   [{msg['priority_score']}] {msg['text'][:60]}...")
        print()
    
    print(f"🟢 Medium (50-69): {len(medium)} messages")
    for msg in medium[:3]:
        print(f"   [{msg['priority_score']}] {msg['text'][:60]}...")
        print()
    
    print(f"⚪ Low (<50): {len(low)} messages")
    for msg in low[:3]:
        print(f"   [{msg['priority_score']}] {msg['text'][:60]}...")
        print()
    
    # Check for @mentions
    your_user_id = "U09NR3RQZQU"  # Your user ID
    mentions = [m for m in messages if f"<@{your_user_id}>" in m['text']]
    print(f"📌 Messages with @mentions: {len(mentions)}")
    for msg in mentions:
        print(f"   [{msg['priority_score']}] {msg['text'][:60]}...")
    
    print()
    print("🎯 Validation Summary:")
    print(f"   - Total messages: {total}")
    print(f"   - Critical: {len(critical)} ({len(critical)/total*100:.1f}%)")
    print(f"   - High: {len(high)} ({len(high)/total*100:.1f}%)")
    print(f"   - Medium: {len(medium)} ({len(medium)/total*100:.1f}%)")
    print(f"   - Low: {len(low)} ({len(low)/total*100:.1f}%)")
    print(f"   - @mentions: {len(mentions)}")

def check_accuracy():
    """Check if prioritization seems accurate"""
    
    print("🔍 Checking Prioritization Accuracy...")
    print("=" * 50)
    
    data = get_inbox_data()
    if not data:
        return
    
    messages = data['messages']
    
    # Look for patterns that should be high priority
    high_priority_indicators = [
        "urgent", "asap", "blocking", "production", "escalation", 
        "decision", "approval", "deadline", "critical"
    ]
    
    # Look for patterns that should be low priority
    low_priority_indicators = [
        "happy", "friday", "coffee", "lol", "meme", "casual",
        "automated", "metrics", "dashboard"
    ]
    
    print("✅ High Priority Indicators Found:")
    for msg in messages:
        text_lower = msg['text'].lower()
        for indicator in high_priority_indicators:
            if indicator in text_lower:
                print(f"   [{msg['priority_score']}] '{indicator}' in: {msg['text'][:50]}...")
                break
    
    print("\n✅ Low Priority Indicators Found:")
    for msg in messages:
        text_lower = msg['text'].lower()
        for indicator in low_priority_indicators:
            if indicator in text_lower:
                print(f"   [{msg['priority_score']}] '{indicator}' in: {msg['text'][:50]}...")
                break
    
    print("\n🎯 Accuracy Assessment:")
    
    # Check if @mentions are prioritized
    your_user_id = "U09NR3RQZQU"  # Your user ID
    mentions = [m for m in messages if f"<@{your_user_id}>" in m['text']]
    high_mention_scores = [m for m in mentions if m['priority_score'] >= 80]
    print(f"   - @mentions prioritized: {len(high_mention_scores)}/{len(mentions)} ({len(high_mention_scores)/max(len(mentions),1)*100:.1f}%)")
    
    # Check if urgent keywords are prioritized
    urgent_messages = [m for m in messages if any(word in m['text'].lower() for word in ['urgent', 'asap', 'blocking'])]
    high_urgent_scores = [m for m in urgent_messages if m['priority_score'] >= 80]
    print(f"   - Urgent keywords prioritized: {len(high_urgent_scores)}/{len(urgent_messages)} ({len(high_urgent_scores)/max(len(urgent_messages),1)*100:.1f}%)")
    
    # Check if casual messages are deprioritized
    casual_messages = [m for m in messages if any(word in m['text'].lower() for word in ['happy', 'friday', 'coffee', 'casual'])]
    low_casual_scores = [m for m in casual_messages if m['priority_score'] < 50]
    print(f"   - Casual messages deprioritized: {len(low_casual_scores)}/{len(casual_messages)} ({len(low_casual_scores)/max(len(casual_messages),1)*100:.1f}%)")

def main():
    """Main validation function"""
    
    print("🔍 Slack Intelligence Prioritization Validator")
    print("=" * 60)
    print()
    
    # Check if server is running
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ Server not responding. Make sure it's running on port {API_PORT}")
            return
    except:
        print(f"❌ Cannot connect to server. Make sure it's running on port {API_PORT}")
        return
    
    print("✅ Server is running")
    print()
    
    # Analyze prioritization
    data = get_inbox_data()
    if data:
        analyze_prioritization(data)
        print()
        check_accuracy()
    else:
        print("❌ No data to analyze")

if __name__ == "__main__":
    main()
