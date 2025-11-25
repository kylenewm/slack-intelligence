#!/usr/bin/env python3
"""
Non-interactive CLI tool to create Jira ticket from the highest priority Slack message.
Includes optional Exa research.
"""

import sys
import asyncio
import logging
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from backend.services.inbox_service import InboxService
from backend.integrations.jira_service import JiraService
from backend.integrations.exa_service import ExaSearchService
from backend.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Create Jira ticket for highest priority message"""
    print("\n" + "="*70)
    print("🎫 CREATE JIRA TICKET - AUTO MODE")
    print("="*70)
    
    # Parse command line args
    do_research = "--research" in sys.argv or "-r" in sys.argv
    message_index = 0  # Default to highest priority
    
    for arg in sys.argv[1:]:
        if arg.startswith("--message="):
            try:
                message_index = int(arg.split("=")[1]) - 1
            except:
                pass
    
    # Initialize services
    inbox = InboxService()
    jira = JiraService()
    exa = ExaSearchService() if do_research else None
    
    if not jira.enabled:
        print("\n❌ Jira not configured!")
        print("Set these environment variables in .env:")
        print("  - JIRA_API_KEY")
        print("  - JIRA_EMAIL")
        print("  - JIRA_DOMAIN")
        print("  - JIRA_PROJECT_KEY")
        sys.exit(1)
    
    print(f"\n✅ Connected to Jira: {jira.base_url}")
    print(f"   Project: {jira.project_key}")
    
    # Fetch high-priority messages
    print("\n📬 Fetching high-priority messages...")
    high_priority = await inbox.get_high_priority(hours_ago=168, limit=20)  # Last week
    
    if not high_priority:
        print("\n❌ No high-priority messages found in the last 7 days")
        print("   Run 'python scripts/sync_once.py' to fetch fresh messages")
        sys.exit(0)
    
    # Display messages
    print(f"\n📋 Found {len(high_priority)} high-priority messages:")
    print("-" * 70)
    
    for i, msg in enumerate(high_priority[:5], 1):  # Show top 5
        score = msg['priority_score']
        user = msg['user_name']
        channel = msg['channel_name']
        text = msg['text'][:60].replace('\n', ' ')
        
        # Color code by priority
        if score >= 90:
            emoji = "🔴"
        elif score >= 75:
            emoji = "🟡"
        else:
            emoji = "🟢"
        
        marker = "👉" if i-1 == message_index else "  "
        print(f"{marker} {emoji} {i}. [{score:3d}] {user} in #{channel}")
        print(f"      {text}...")
    
    print("-" * 70)
    
    # Select message
    if message_index >= len(high_priority):
        message_index = 0
    
    selected_msg = high_priority[message_index]
    
    # Display selected message
    print("\n" + "="*70)
    print("📝 CREATING TICKET FOR:")
    print("="*70)
    print(f"From: {selected_msg['user_name']} in #{selected_msg['channel_name']}")
    print(f"Priority: {selected_msg['priority_score']}/100")
    print(f"Reason: {selected_msg['priority_reason']}")
    print(f"\nMessage:\n{selected_msg['text'][:200]}...")
    print("="*70)
    
    # Run research if requested
    research_summary = None
    ticket_type = "general_task"
    
    if do_research and exa:
        print("\n🔍 Running Exa research...")
        
        research = await exa.research_for_ticket(selected_msg)
        detection = research.get('detection', {})
        ticket_type = detection.get('ticket_type', 'general_task')
        
        print(f"   ✅ Type: {ticket_type}")
        print(f"   📊 Research: {detection.get('needs_research', False)}")
        
        if research.get('sources'):
            print(f"   📚 Found {len(research['sources'])} sources")
            research_summary = research.get('research_summary')
        else:
            print("   ℹ️  No research performed")
    
    # Determine ticket details
    summary = selected_msg['text'][:100]
    issue_type = jira._determine_issue_type(ticket_type, selected_msg['text'])
    
    print(f"\n🎫 Creating ticket:")
    print(f"   Title: {summary[:50]}...")
    print(f"   Type: {issue_type}")
    print(f"   Research: {'✅ Included' if research_summary else '❌ None'}")
    
    # Create ticket
    print("\n🚀 Creating Jira ticket...")
    
    result = await jira.create_ticket(
        message=selected_msg,
        summary=summary,
        issue_type=issue_type,
        research_summary=research_summary,
        ticket_type=ticket_type
    )
    
    # Display result
    print("\n" + "="*70)
    if result.get('success'):
        print("✅ SUCCESS! Jira ticket created")
        print("="*70)
        print(f"\n🎫 Ticket: {result['jira_key']}")
        print(f"🔗 URL: {result['jira_url']}")
        print(f"\n💡 You can now view and edit this ticket in Jira")
    else:
        print("❌ FAILED to create ticket")
        print("="*70)
        print(f"\nError: {result.get('error')}")
        print("\nTroubleshooting:")
        print("  - Run 'python scripts/test_jira.py' to verify credentials")
        print("  - Check that issue type exists in your project")
        print("  - Verify project permissions")
    
    print("="*70)
    
    # Show usage
    if result.get('success'):
        print("\n💡 Usage:")
        print("   Create ticket with research:")
        print("     python scripts/create_jira_ticket_auto.py --research")
        print("   Create ticket for specific message (by position):")
        print("     python scripts/create_jira_ticket_auto.py --message=2")
    
    print()


if __name__ == "__main__":
    asyncio.run(main())

