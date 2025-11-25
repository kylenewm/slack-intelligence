"""
Test script to verify Context Engine functionality.
Checks if the AI is "aware" of Traverse.ai identity and codebase structure.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.context_service import ContextService
from backend.integrations.exa_service import ExaSearchService

async def test_context_service():
    print("\n🔍 Testing Context Service...")
    service = ContextService()
    
    # Test 1: Identity Load
    context = await service.get_full_context()
    
    if "Traverse.ai" in context:
        print("✅ Identity loaded successfully")
    else:
        print("❌ Identity NOT found in context")
        
    # Test 2: Codebase Scan
    if "slack_ingester.py" in context:
        print("✅ Codebase scan active (found slack_ingester.py)")
    else:
        print("❌ Codebase scan failed")
        
    # Test 3: Memory Load
    if "Slack API Rate Limiting" in context:
        print("✅ Institutional Memory loaded")
    else:
        print("❌ Institutional Memory failed")

async def test_exa_integration():
    print("\n🤖 Testing Exa Context Integration...")
    
    # We need OpenAI key for this
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set, skipping LLM test")
        return

    exa = ExaSearchService()
    
    # Test Message
    msg = {
        "text": "We are seeing 429 errors when fetching messages from Slack.",
        "channel_name": "engineering",
        "user_name": "Kyle",
        "priority_score": 95
    }
    
    print(f"Input Message: {msg['text']}")
    
    # 1. Detection
    print("1. Running Detection...")
    detection = await exa.detect_ticket_type(msg)
    print(f"   Type: {detection.get('ticket_type')}")
    print(f"   Reason: {detection.get('reason')}")
    
    # 2. Context-Aware Query
    print("2. Generating Search Query...")
    query = await exa.build_search_query(
        msg, 
        detection.get('ticket_type'),
        detection.get('research_type')
    )
    print(f"   Query: {query}")
    
    # Check if query inferred context (e.g. mentions python/slack_sdk)
    if "slack" in query.lower() or "python" in query.lower():
        print("✅ Query successfully inferred technical context")
    else:
        print("⚠️  Query might be too generic")

if __name__ == "__main__":
    asyncio.run(test_context_service())
    asyncio.run(test_exa_integration())

