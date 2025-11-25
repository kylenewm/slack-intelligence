#!/usr/bin/env python3
"""
Hybrid notification system with multiple notification methods.
Uses desktop notifications, audio alerts, and console output.
"""

import os
import time
import subprocess
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API port from environment (default 8000)
API_PORT = int(os.getenv("API_PORT", "8000"))
API_BASE = f"http://localhost:{API_PORT}"
CHECK_INTERVAL = 600  # 10 minutes in seconds (production)

# Track which messages we've already notified about
notified_message_ids = set()

def check_server():
    """Check if the API server is running"""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_critical_messages():
    """Get messages that need immediate attention"""
    try:
        response = requests.get(f"{API_BASE}/api/slack/inbox?view=needs_response&limit=10")
        if response.status_code == 200:
            data = response.json()
            return data.get('messages', [])
        return []
    except Exception as e:
        print(f"❌ Error fetching messages: {e}")
        return []

def send_hybrid_notification(title, message, count=1):
    """Send notification using multiple methods"""
    
    # Method 1: Desktop notification (osascript)
    try:
        subprocess.run(['osascript', '-e', f'display notification "{message}" with title "{title}"'], 
                      check=False)
    except:
        pass
    
    # Method 2: Audio notification
    try:
        if count == 1:
            subprocess.run(['say', f'Urgent Slack message: {message[:50]}'], check=False)
        else:
            subprocess.run(['say', f'{count} urgent Slack messages need your attention'], check=False)
    except:
        pass
    
    # Method 3: Console notification (always works)
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"\n🔔 [{timestamp}] {title}")
    print(f"   {message}")
    print(f"   Check your Slack for details!")
    print()

def notify_critical_messages(messages):
    """Send notifications for new critical messages"""
    
    # Filter out messages we've already notified about
    new_messages = [m for m in messages if m['id'] not in notified_message_ids]
    
    if not new_messages:
        return 0
    
    # Send hybrid notification
    count = len(new_messages)
    
    if count == 1:
        msg = new_messages[0]
        title = "🔴 URGENT Slack Message"
        body = f"[{msg['priority_score']}] {msg['user_name']} in #{msg['channel_name']}: {msg['text'][:60]}"
        send_hybrid_notification(title, body, 1)
    else:
        title = f"🔴 {count} URGENT Slack Messages"
        preview = f"{count} urgent messages need your attention"
        send_hybrid_notification(title, preview, count)
    
    # Mark as notified
    for msg in new_messages:
        notified_message_ids.add(msg['id'])
    
    return count

def monitor_loop():
    """Main monitoring loop"""
    
    print("🔔 Hybrid Slack Intelligence Notification Monitor")
    print("=" * 60)
    print(f"✅ Checking for critical messages every {CHECK_INTERVAL//60} minutes")
    print(f"🎯 Notifying about messages with score ≥ 90")
    print(f"🔊 Using: Desktop notifications + Audio alerts + Console output")
    print()
    print("Press Ctrl+C to stop")
    print()
    
    iteration = 0
    
    try:
        while True:
            iteration += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Check server health
            if not check_server():
                print(f"[{timestamp}] ⚠️  Server not running. Waiting...")
                time.sleep(60)
                continue
            
            # Get critical messages
            messages = get_critical_messages()
            
            if messages:
                # Notify about new ones
                notified = notify_critical_messages(messages)
                
                if notified > 0:
                    print(f"[{timestamp}] 🔔 Sent hybrid notification for {notified} new critical message(s)")
                else:
                    print(f"[{timestamp}] ✓ {len(messages)} critical message(s) (already notified)")
            else:
                print(f"[{timestamp}] ✓ No critical messages")
            
            # Wait for next check
            if iteration == 1:
                print(f"\n⏰ Next check in {CHECK_INTERVAL//60} minutes...")
            
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n👋 Stopped monitoring")
        print(f"📊 Sent notifications for {len(notified_message_ids)} unique messages")

def test_notification():
    """Test the hybrid notification system"""
    print("🧪 Testing hybrid notification system...")
    send_hybrid_notification(
        "Slack Intelligence Test",
        "Hybrid notification system is working! You should see this message in multiple ways.",
        1
    )
    print("✅ Test notification sent using all methods!")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test mode
        test_notification()
    else:
        # Normal monitoring mode
        monitor_loop()
