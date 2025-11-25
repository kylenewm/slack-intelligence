#!/usr/bin/env python3
"""
Interactive CLI tool to create Jira tickets from Slack messages.
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
    level=logging.WARNING,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Interactive Jira ticket creation"""
    print("\n" + "="*70)
    print("🎫 CREATE JIRA TICKET FROM SLACK MESSAGE")
    print("="*70)
    
    # Initialize services
    inbox = InboxService()
    jira = JiraService()
    exa = ExaSearchService()
    
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
    
    for i, msg in enumerate(high_priority, 1):
        score = msg['priority_score']
        user = msg['user_name']
        channel = msg['channel_name']
        text = msg['text'][:80].replace('\n', ' ')
        
        # Color code by priority
        if score >= 90:
            emoji = "🔴"
        elif score >= 75:
            emoji = "🟡"
        else:
            emoji = "🟢"
        
        print(f"{emoji} {i:2d}. [{score:3d}] {user} in #{channel}")
        print(f"      {text}...")
        print()
    
    # Let user select message
    print("-" * 70)
    try:
        choice = input("\n👉 Select message number (or 'q' to quit): ").strip()
        
        if choice.lower() == 'q':
            print("Cancelled.")
            sys.exit(0)
        
        choice_num = int(choice)
        if choice_num < 1 or choice_num > len(high_priority):
            print("❌ Invalid selection")
            sys.exit(1)
        
        selected_msg = high_priority[choice_num - 1]
        
    except (ValueError, KeyboardInterrupt):
        print("\n❌ Invalid input or cancelled")
        sys.exit(1)
    
    # Display selected message
    print("\n" + "="*70)
    print("📝 SELECTED MESSAGE:")
    print("="*70)
    print(f"From: {selected_msg['user_name']} in #{selected_msg['channel_name']}")
    print(f"Priority: {selected_msg['priority_score']}/100")
    print(f"Reason: {selected_msg['priority_reason']}")
    print(f"\nMessage:\n{selected_msg['text']}")
    print("="*70)
    
    # Ask about research
    research_summary = None
    ticket_type = "general_task"
    
    print("\n🔍 Would you like to run Exa research for this ticket?")
    print("   (Searches for solutions, documentation, best practices)")
    do_research = input("   Run research? [Y/n]: ").strip().lower()
    
    if do_research != 'n':
        print("\n🔍 Running Exa research...")
        print("   1. Detecting ticket type...")
        
        research = await exa.research_for_ticket(selected_msg)
        detection = research.get('detection', {})
        ticket_type = detection.get('ticket_type', 'general_task')
        
        print(f"   ✅ Type: {ticket_type}")
        print(f"   📊 Research needed: {detection.get('needs_research', False)}")
        
        if research.get('sources'):
            print(f"   📚 Found {len(research['sources'])} sources")
            research_summary = research.get('research_summary')
            
            if research_summary:
                print("\n" + "-"*70)
                print("📄 RESEARCH SUMMARY:")
                print("-"*70)
                print(research_summary[:500] + "..." if len(research_summary) > 500 else research_summary)
                print("-"*70)
        else:
            print("   ℹ️  No research performed (not needed for this type)")
    
    # Ask for ticket customization
    print("\n🎫 Ticket Details:")
    print("-" * 70)
    
    default_summary = selected_msg['text'][:100]
    summary = input(f"Title [{default_summary[:50]}...]: ").strip()
    if not summary:
        summary = default_summary
    
    print("\n📋 Issue Type Options: Bug, Task, Story, Epic")
    default_type = jira._determine_issue_type(ticket_type, selected_msg['text'])
    issue_type = input(f"Issue Type [{default_type}]: ").strip()
    if not issue_type:
        issue_type = default_type
    
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
    print()


if __name__ == "__main__":
    asyncio.run(main())

