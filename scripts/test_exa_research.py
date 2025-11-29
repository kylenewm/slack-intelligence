#!/usr/bin/env python3
"""
Test Exa Research Quality Across Multiple Scenarios

Tests research quality for:
1. Technical bugs
2. Feature planning
3. Product decisions
4. Competitive analysis
"""

import sys
import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from backend.integrations.exa_service import ExaSearchService
from backend.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Test Scenarios
TEST_SCENARIOS = [
    {
        "id": "bug_technical",
        "name": "🐛 Technical Bug",
        "message": {
            "text": "API returning 500 errors on checkout endpoint. Started after last deploy. Users can't complete purchases.",
            "channel_name": "engineering-alerts",
            "user_name": "Marcus",
            "priority_score": 95
        },
        "expected_type": "bug",
        "quality_criteria": [
            "Finds Stack Overflow or GitHub issues",
            "Mentions FastAPI or Python-specific solutions",
            "Provides specific debugging steps or code patterns"
        ]
    },
    {
        "id": "feature_planning",
        "name": "📋 Feature Planning",
        "message": {
            "text": "Should we add OAuth or SAML for enterprise auth? Need to decide before Q1 planning. What do similar B2B products use?",
            "channel_name": "product",
            "user_name": "Jordan",
            "priority_score": 75
        },
        "expected_type": "feature_request",
        "quality_criteria": [
            "Finds comparison articles or case studies",
            "Discusses tradeoffs between OAuth and SAML",
            "References what other B2B SaaS companies use"
        ]
    },
    {
        "id": "product_decision",
        "name": "🎯 Product Decision",
        "message": {
            "text": "What's the best approach for real-time notifications - WebSockets or polling? Need to support 1000+ concurrent users.",
            "channel_name": "engineering",
            "user_name": "Kyle",
            "priority_score": 70
        },
        "expected_type": "general_task",
        "quality_criteria": [
            "Compares WebSockets vs polling approaches",
            "Discusses scalability considerations",
            "References specific frameworks or patterns"
        ]
    },
    {
        "id": "competitive_analysis",
        "name": "🔍 Competitive Analysis",
        "message": {
            "text": "How does Slack handle message prioritization? Curious if they use AI or just keyword filters.",
            "channel_name": "product",
            "user_name": "Lisa",
            "priority_score": 60
        },
        "expected_type": "general_task",
        "quality_criteria": [
            "Finds Slack product documentation or reviews",
            "Discusses how competing products solve prioritization",
            "Provides recent information (not outdated)"
        ]
    }
]


async def test_scenario(exa: ExaSearchService, scenario: dict) -> dict:
    """Test a single research scenario"""
    print("\n" + "="*70)
    print(f"{scenario['name']}: {scenario['message']['text'][:60]}...")
    print("="*70)
    
    result = {
        "scenario_id": scenario["id"],
        "scenario_name": scenario["name"],
        "message": scenario["message"],
        "expected_type": scenario["expected_type"],
        "quality_criteria": scenario["quality_criteria"],
        "timestamp": datetime.utcnow().isoformat()
    }
    
    try:
        # Run research
        print("\n🔍 Running research...")
        research = await exa.research_for_ticket(scenario["message"])
        
        # Extract results
        detection = research.get('detection', {})
        sources = research.get('sources', [])
        summary = research.get('research_summary')
        
        result["detection"] = detection
        result["search_query"] = "N/A"  # Not directly exposed, but we can see it in logs
        result["sources_count"] = len(sources)
        result["sources"] = sources
        result["research_summary"] = summary
        result["success"] = True
        
        # Display results
        print(f"\n✅ Detection Results:")
        print(f"   Ticket Type: {detection.get('ticket_type', 'unknown')}")
        print(f"   Needs Research: {detection.get('needs_research', False)}")
        print(f"   Research Type: {detection.get('research_type', 'none')}")
        print(f"   Reason: {detection.get('reason', 'N/A')[:100]}...")
        
        if sources:
            print(f"\n📚 Found {len(sources)} sources:")
            for i, source in enumerate(sources[:3], 1):  # Show first 3
                print(f"   {i}. {source.get('title', 'Untitled')}")
                print(f"      URL: {source.get('url', 'N/A')}")
                print(f"      Preview: {source.get('text', '')[:100]}...")
        else:
            print("\n⚠️  No sources found (AI determined research not needed)")
        
        if summary:
            print(f"\n💡 Research Summary:")
            print(f"   {summary[:300]}...")
        else:
            print("\n⚠️  No summary generated")
        
        # Quality assessment prompts
        print(f"\n📊 Quality Criteria to Check:")
        for i, criteria in enumerate(scenario["quality_criteria"], 1):
            print(f"   {i}. {criteria}")
        
    except Exception as e:
        print(f"\n❌ Error during research: {e}")
        result["success"] = False
        result["error"] = str(e)
    
    return result


async def main():
    """Run all test scenarios"""
    print("\n" + "="*70)
    print("🧪 EXA RESEARCH QUALITY TEST")
    print("="*70)
    
    # Check configuration
    if not settings.EXA_API_KEY:
        print("\n❌ EXA_API_KEY not set in .env")
        print("   This test requires Exa API access")
        sys.exit(1)
    
    if not settings.OPENAI_API_KEY:
        print("\n❌ OPENAI_API_KEY not set")
        sys.exit(1)
    
    print(f"\n📋 Testing {len(TEST_SCENARIOS)} scenarios:")
    for scenario in TEST_SCENARIOS:
        print(f"   • {scenario['name']}")
    
    # Initialize service
    exa = ExaSearchService()
    
    # Run all scenarios
    results = []
    for scenario in TEST_SCENARIOS:
        result = await test_scenario(exa, scenario)
        results.append(result)
    
    # Save results
    output_dir = Path(__file__).parent.parent / "simulations"
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = output_dir / f"exa_test_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    successful = sum(1 for r in results if r.get("success"))
    failed = len(results) - successful
    
    print(f"\n✅ Successful: {successful}/{len(results)}")
    print(f"❌ Failed: {failed}/{len(results)}")
    
    if successful > 0:
        avg_sources = sum(r.get("sources_count", 0) for r in results if r.get("success")) / successful
        print(f"📚 Avg Sources: {avg_sources:.1f} per scenario")
        
        with_summary = sum(1 for r in results if r.get("success") and r.get("research_summary"))
        print(f"💡 Generated Summaries: {with_summary}/{successful}")
    
    print(f"\n💾 Results saved to: {output_file}")
    
    print("\n" + "="*70)
    print("🔍 NEXT STEPS:")
    print("="*70)
    print("1. Review the output above for each scenario")
    print("2. Check if sources are relevant and recent")
    print("3. Evaluate if summaries are actionable")
    print("4. Open the JSON file for detailed inspection")
    print(f"   {output_file}")
    print("\nIf quality is good, create Jira tickets with:")
    print("   python scripts/create_jira_ticket_auto.py --research")
    print()


if __name__ == "__main__":
    asyncio.run(main())


