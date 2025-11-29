#!/usr/bin/env python3
"""
Test Code Bug Analyzer

Tests the CodeBugAnalyzer service with realistic bug scenarios to verify:
1. Error patterns are extracted correctly
2. Codebase search finds relevant files
3. Institutional memory matches past issues
4. Debugging steps are specific and actionable
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

from backend.services.code_bug_analyzer import CodeBugAnalyzer
from backend.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Test Bug Scenarios
TEST_BUGS = [
    {
        "id": "database_error",
        "name": "Database Integrity Error",
        "message": {
            "text": "IntegrityError when saving message to database. Foreign key constraint failed on channel_id. Stack trace shows error in cache_service.py line 45.",
            "channel_name": "engineering-alerts",
            "user_name": "AlertBot",
            "priority_score": 95
        },
        "expected_patterns": {
            "exception_types": ["IntegrityError"],
            "file_mentions": ["cache_service.py"]
        },
        "expected_memory_match": "SQLAlchemy Object vs Dict Confusion"
    },
    {
        "id": "rate_limit",
        "name": "Slack API Rate Limit",
        "message": {
            "text": "Slack API returning 429 errors. Ingestion worker crashed. We're not handling the Retry-After header properly.",
            "channel_name": "incidents",
            "user_name": "PagerDuty",
            "priority_score": 98
        },
        "expected_patterns": {
            "status_codes": ["429"],
            "keywords": ["rate limit", "crash"]
        },
        "expected_memory_match": "Slack API Rate Limiting"
    },
    {
        "id": "notion_sync",
        "name": "Notion Sync Failure",
        "message": {
            "text": "Notion pages showing raw JSON instead of formatted text. The rich text blocks in notion_service.py aren't converting properly. ValidationError on nested blocks.",
            "channel_name": "product-feedback",
            "user_name": "Sarah",
            "priority_score": 85
        },
        "expected_patterns": {
            "exception_types": ["ValidationError"],
            "file_mentions": ["notion_service.py"]
        },
        "expected_memory_match": "Notion Block Format Errors"
    },
    {
        "id": "api_500",
        "name": "API 500 Error",
        "message": {
            "text": "500 Internal Server Error on /api/slack/sync endpoint. Started after the latest deploy. TypeError in routes.py - 'NoneType' has no attribute 'get'",
            "channel_name": "engineering-alerts",
            "user_name": "Marcus",
            "priority_score": 92
        },
        "expected_patterns": {
            "status_codes": ["500"],
            "exception_types": ["TypeError"],
            "file_mentions": ["routes.py"]
        },
        "expected_memory_match": None  # No specific match expected
    },
    {
        "id": "jira_adf",
        "name": "Jira Description Error",
        "message": {
            "text": "Jira API rejecting ticket creation with error: 'Operation value must be an Atlassian Document'. Plain text descriptions not working in jira_service.py",
            "channel_name": "engineering",
            "user_name": "Kyle",
            "priority_score": 80
        },
        "expected_patterns": {
            "file_mentions": ["jira_service.py"]
        },
        "expected_memory_match": "Jira Description Must Be ADF"
    }
]


async def test_scenario(analyzer: CodeBugAnalyzer, scenario: dict) -> dict:
    """Test a single bug scenario."""
    print("\n" + "="*70)
    print(f"🐛 {scenario['name']}")
    print("="*70)
    print(f"Message: {scenario['message']['text'][:80]}...")
    
    result = {
        "scenario_id": scenario["id"],
        "scenario_name": scenario["name"],
        "message": scenario["message"],
        "timestamp": datetime.utcnow().isoformat()
    }
    
    try:
        # Run analysis
        analysis = await analyzer.analyze(scenario["message"])
        result["analysis"] = analysis
        result["success"] = True
        
        # Display results
        print(f"\n✅ Analysis Complete")
        
        # Check patterns
        patterns = analysis.get("patterns", {})
        print(f"\n📋 Extracted Patterns:")
        
        expected = scenario.get("expected_patterns", {})
        
        if patterns.get("exception_types"):
            match = any(e in patterns["exception_types"] for e in expected.get("exception_types", []))
            status = "✅" if match or not expected.get("exception_types") else "⚠️"
            print(f"   {status} Exception Types: {patterns['exception_types']}")
        
        if patterns.get("status_codes"):
            match = any(c in patterns["status_codes"] for c in expected.get("status_codes", []))
            status = "✅" if match or not expected.get("status_codes") else "⚠️"
            print(f"   {status} Status Codes: {patterns['status_codes']}")
        
        if patterns.get("file_mentions"):
            match = any(f in patterns["file_mentions"] for f in expected.get("file_mentions", []))
            status = "✅" if match or not expected.get("file_mentions") else "⚠️"
            print(f"   {status} File Mentions: {patterns['file_mentions']}")
        
        if patterns.get("keywords"):
            print(f"   ℹ️  Keywords: {patterns['keywords'][:5]}")
        
        # Codebase matches
        codebase_matches = analysis.get("codebase_matches", [])
        if codebase_matches:
            print(f"\n📂 Codebase Matches ({len(codebase_matches)}):")
            for match in codebase_matches[:3]:
                print(f"   • {match['file']}", end="")
                if match.get('line'):
                    print(f" (line {match['line']})")
                else:
                    print()
                if match.get('snippet'):
                    print(f"     └─ {match['snippet'][:60]}...")
        else:
            print(f"\n📂 Codebase Matches: None found")
        
        # Memory matches
        memory_matches = analysis.get("memory_matches", [])
        expected_memory = scenario.get("expected_memory_match")
        if memory_matches:
            print(f"\n🧠 Institutional Memory Matches ({len(memory_matches)}):")
            for match in memory_matches[:3]:
                # Check if expected match was found
                is_expected = expected_memory and expected_memory.lower() in match['issue'].lower()
                status = "✅" if is_expected else "•"
                print(f"   {status} {match['issue']} (relevance: {match['relevance']:.0%})")
                if match.get('solution'):
                    print(f"     └─ {match['solution'][:80]}...")
            
            if expected_memory:
                found = any(expected_memory.lower() in m['issue'].lower() for m in memory_matches)
                if not found:
                    print(f"   ⚠️  Expected to find: '{expected_memory}'")
        else:
            print(f"\n🧠 Institutional Memory: No matches")
            if expected_memory:
                print(f"   ⚠️  Expected to find: '{expected_memory}'")
        
        # Debugging steps
        debugging_steps = analysis.get("debugging_steps", [])
        if debugging_steps:
            print(f"\n🔧 Debugging Steps ({len(debugging_steps)}):")
            for i, step in enumerate(debugging_steps[:5], 1):
                print(f"   {i}. {step}")
        
        # Summary
        summary = analysis.get("summary", "")
        if summary:
            print(f"\n📊 Summary: {summary[:100]}...")
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        result["success"] = False
        result["error"] = str(e)
        import traceback
        traceback.print_exc()
    
    return result


async def main():
    """Run all test scenarios."""
    print("\n" + "="*70)
    print("🔍 CODE BUG ANALYZER TEST SUITE")
    print("="*70)
    
    print(f"\n📋 Testing {len(TEST_BUGS)} bug scenarios:")
    for scenario in TEST_BUGS:
        print(f"   • {scenario['name']}")
    
    # Initialize analyzer
    analyzer = CodeBugAnalyzer()
    
    # Run all scenarios
    results = []
    for scenario in TEST_BUGS:
        result = await test_scenario(analyzer, scenario)
        results.append(result)
    
    # Save results
    output_dir = Path(__file__).parent.parent / "simulations"
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = output_dir / f"bug_analyzer_test_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    successful = sum(1 for r in results if r.get("success"))
    failed = len(results) - successful
    
    print(f"\n✅ Successful: {successful}/{len(results)}")
    print(f"❌ Failed: {failed}/{len(results)}")
    
    # Quality metrics
    if successful > 0:
        successful_results = [r for r in results if r.get("success")]
        
        avg_memory_matches = sum(
            len(r.get("analysis", {}).get("memory_matches", []))
            for r in successful_results
        ) / successful
        
        avg_codebase_matches = sum(
            len(r.get("analysis", {}).get("codebase_matches", []))
            for r in successful_results
        ) / successful
        
        avg_steps = sum(
            len(r.get("analysis", {}).get("debugging_steps", []))
            for r in successful_results
        ) / successful
        
        print(f"\n📊 Quality Metrics:")
        print(f"   Avg Memory Matches: {avg_memory_matches:.1f} per scenario")
        print(f"   Avg Codebase Matches: {avg_codebase_matches:.1f} per scenario")
        print(f"   Avg Debugging Steps: {avg_steps:.1f} per scenario")
    
    print(f"\n💾 Results saved to: {output_file}")
    
    print("\n" + "="*70)
    print("🔍 NEXT STEPS:")
    print("="*70)
    print("1. Review the output above for each scenario")
    print("2. Check if memory matches are relevant")
    print("3. Verify debugging steps are actionable")
    print("4. Test end-to-end with Jira ticket creation:")
    print("   python scripts/create_jira_ticket_auto.py --research")
    print()


if __name__ == "__main__":
    asyncio.run(main())


