#!/usr/bin/env python3
"""
Production monitoring script.
Shows current status and recent activity.
"""

import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API port from environment (default 8000)
API_PORT = int(os.getenv("API_PORT", "8000"))
API_BASE = f"http://localhost:{API_PORT}"

def get_stats():
    """Get current system statistics"""
    try:
        response = requests.get(f"{API_BASE}/api/slack/stats")
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except:
        return None

def get_inbox_summary():
    """Get inbox summary by category"""
    try:
        views = ['needs_response', 'high_priority', 'fyi', 'low_priority']
        summary = {}
        
        for view in views:
            response = requests.get(f"{API_BASE}/api/slack/inbox?view={view}&limit=10")
            if response.status_code == 200:
                data = response.json()
                summary[view] = len(data.get('messages', []))
            else:
                summary[view] = 0
        
        return summary
    except:
        return None

def check_recent_syncs():
    """Check if recent syncs are working"""
    try:
        # Try a small sync to test connectivity
        response = requests.post(f"{API_BASE}/api/slack/sync?hours_ago=1", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                'status': 'success',
                'new_messages': data['fetch']['new_messages'],
                'duration': data['duration_seconds']
            }
        else:
            return {'status': 'failed', 'error': f"HTTP {response.status_code}"}
    except Exception as e:
        return {'status': 'failed', 'error': str(e)}

def main():
    """Show production monitoring dashboard"""
    print("📊 Slack Intelligence Production Monitor")
    print("=" * 60)
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check server health
    try:
        health_response = requests.get(f"{API_BASE}/health", timeout=5)
        if health_response.status_code == 200:
            print("🟢 Server Status: RUNNING")
        else:
            print("🔴 Server Status: ERROR")
            return
    except:
        print("🔴 Server Status: OFFLINE")
        return
    
    # Get statistics
    stats = get_stats()
    if stats:
        print(f"📈 Total Messages: {stats.get('total_messages', 0)}")
        print(f"📅 Last Sync: {stats.get('last_sync', 'Unknown')}")
        print(f"🔄 Syncs Today: {stats.get('syncs_today', 0)}")
    else:
        print("❌ Cannot fetch statistics")
    
    print()
    
    # Get inbox summary
    inbox = get_inbox_summary()
    if inbox:
        print("📬 Inbox Summary:")
        print(f"   🚨 Needs Response: {inbox.get('needs_response', 0)}")
        print(f"   🔥 High Priority: {inbox.get('high_priority', 0)}")
        print(f"   📋 FYI: {inbox.get('fyi', 0)}")
        print(f"   ⬇️  Low Priority: {inbox.get('low_priority', 0)}")
    else:
        print("❌ Cannot fetch inbox summary")
    
    print()
    
    # Test recent sync
    print("🔄 Testing Recent Sync...")
    sync_result = check_recent_syncs()
    if sync_result['status'] == 'success':
        print(f"   ✅ Sync successful: {sync_result['new_messages']} new messages in {sync_result['duration']:.1f}s")
    else:
        print(f"   ❌ Sync failed: {sync_result['error']}")
    
    print()
    print("=" * 60)
    print("💡 Commands:")
    print("   Check inbox: python scripts/check_inbox.py")
    print(f"   Manual sync: curl -X POST 'http://localhost:{API_PORT}/api/slack/sync?hours_ago=2'")
    print("   View logs: tail -f logs/slack_intelligence.log")

if __name__ == "__main__":
    main()
