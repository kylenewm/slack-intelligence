#!/usr/bin/env python3
"""
Test Jira API connection and credentials.
"""

import sys
import asyncio
import logging
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from backend.integrations.jira_service import JiraService
from backend.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Test Jira connection and credentials"""
    print("\n" + "="*60)
    print("🔧 JIRA CONNECTION TEST")
    print("="*60)
    
    # Check configuration
    print("\n📋 Configuration:")
    print(f"   Domain: {settings.JIRA_DOMAIN}")
    print(f"   Project: {settings.JIRA_PROJECT_KEY}")
    print(f"   Email: {settings.JIRA_EMAIL}")
    print(f"   API Key: {'✅ Set' if settings.JIRA_API_KEY else '❌ Missing'}")
    
    # Initialize service
    jira = JiraService()
    
    if not jira.enabled:
        print("\n❌ Jira not properly configured")
        print("\nRequired environment variables:")
        print("  - JIRA_API_KEY")
        print("  - JIRA_EMAIL")
        print("  - JIRA_DOMAIN")
        print("  - JIRA_PROJECT_KEY")
        sys.exit(1)
    
    print(f"\n✅ Jira client initialized")
    print(f"   Base URL: {jira.base_url}")
    
    # Create a test ticket
    print("\n🎫 Creating test ticket...")
    
    test_message = {
        "text": "TEST: Jira Integration - Please delete this ticket",
        "user_name": "Slack Intelligence (Test)",
        "channel_name": "test",
        "priority_score": 50,
        "priority_reason": "Test ticket for Jira integration verification",
        "timestamp": "2024-01-01T00:00:00Z",
        "link": "https://slack.com"
    }
    
    result = await jira.create_ticket(
        message=test_message,
        summary="TEST: Jira Integration Verification",
        issue_type="Task",
        priority="Low",
        labels=["test", "slack-intelligence"]
    )
    
    print("\n" + "="*60)
    if result.get('success'):
        print("✅ TEST PASSED!")
        print(f"\n🎉 Successfully created Jira ticket:")
        print(f"   Key: {result['jira_key']}")
        print(f"   URL: {result['jira_url']}")
        print(f"\n💡 You can now delete this test ticket from Jira")
    else:
        print("❌ TEST FAILED!")
        print(f"\nError: {result.get('error')}")
        print("\nCommon issues:")
        print("  - Invalid API token")
        print("  - Wrong domain or project key")
        print("  - Missing Jira permissions")
        print("  - Project doesn't exist")
    
    print("="*60)
    print()


if __name__ == "__main__":
    asyncio.run(main())

