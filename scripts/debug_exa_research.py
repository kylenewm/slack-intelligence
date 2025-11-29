#!/usr/bin/env python3
"""
Interactive Exa Research Debugger

Shows you EXACTLY what's happening at each step:
1. What message is being analyzed
2. What ticket type is detected
3. What search query is generated
4. What sources are found
5. What the summary looks like

NO Jira creation, NO complexity - just pure visibility.
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from backend.integrations.exa_service import ExaSearchService
from backend.services.inbox_service import InboxService
from backend.config import settings


async def main():
    print("\n" + "="*80)
    print("🔬 EXA RESEARCH DEBUGGER - Step-by-Step Visibility")
    print("="*80)
    
    # Check config
    if not settings.EXA_API_KEY:
        print("\n❌ EXA_API_KEY not set in .env")
        sys.exit(1)
    
    if not settings.OPENAI_API_KEY:
        print("\n❌ OPENAI_API_KEY not set in .env")
        sys.exit(1)
    
    # Check for command line argument
    message_index = None
    for arg in sys.argv[1:]:
        if arg.startswith("--message="):
            try:
                message_index = int(arg.split("=")[1]) - 1
            except:
                pass
    
    # Get messages
    inbox = InboxService()
    messages = await inbox.get_all(hours_ago=168, limit=30)
    
    if not messages:
        print("\n❌ No messages found in database")
        print("   Run 'python scripts/sync_once.py' to fetch messages")
        sys.exit(1)
    
    print(f"\n📬 Found {len(messages)} messages:\n")
    
    for i, msg in enumerate(messages[:15], 1):
        text = msg['text'][:60].replace('\n', ' ')
        score = msg['priority_score']
        user = msg['user_name'][:15]
        marker = "👉" if message_index is not None and i-1 == message_index else "  "
        print(f"{marker} {i:2d}. [{score:3d}] {user:15s} - {text}...")
    
    # Let user pick or use command line arg
    if message_index is not None:
        if message_index >= len(messages):
            print(f"\n⚠️  Index {message_index + 1} out of range, using first message")
            message_index = 0
        selected = messages[message_index]
        print(f"\n👉 Using message #{message_index + 1} (from command line)")
    else:
        try:
            choice = input("\n👉 Select message number (1-15) or press Enter for #1: ")
            if choice.strip():
                message_index = int(choice) - 1
                selected = messages[message_index]
            else:
                selected = messages[0]
        except:
            print("Invalid choice, using first message")
            selected = messages[0]
    
    print("\n" + "="*80)
    print("📝 SELECTED MESSAGE")
    print("="*80)
    print(f"User: {selected['user_name']}")
    print(f"Channel: #{selected['channel_name']}")
    print(f"Priority: {selected['priority_score']}/100")
    print(f"\n{selected['text']}\n")
    
    # Initialize Exa
    exa = ExaSearchService()
    
    # STEP 1: Ticket Type Detection
    print("="*80)
    print("🤖 STEP 1: TICKET TYPE DETECTION")
    print("="*80)
    print("Asking OpenAI to classify this message...")
    start = datetime.now()
    
    detection = await exa.detect_ticket_type(selected)
    
    elapsed = (datetime.now() - start).total_seconds()
    print(f"\n✅ Result ({elapsed:.1f}s):")
    print(f"   Ticket Type: {detection.get('ticket_type')}")
    print(f"   Needs Research: {detection.get('needs_research')}")
    print(f"   Research Type: {detection.get('research_type')}")
    print(f"   Reason: {detection.get('reason')}")
    
    # Check if it's a bug - will route to CodeBugAnalyzer
    if detection.get('ticket_type') in ['bug', 'technical_error']:
        print("\n" + "="*80)
        print("🐛 BUG DETECTED - Would route to CodeBugAnalyzer")
        print("="*80)
        print("This message would use CodeBugAnalyzer instead of Exa.")
        print("Run 'python scripts/test_code_bug_analyzer.py' to test that flow.")
        print("\nWant to continue with Exa anyway? (This will show what Exa would find)")
        
        try:
            cont = input("Continue with Exa? (y/n): ").strip().lower()
            if cont != 'y':
                print("\nExiting. Use --message=N with a non-bug message to test Exa.")
                return
        except:
            return
    
    if not detection.get('needs_research'):
        print("\n" + "="*80)
        print("⚠️  RESEARCH NOT NEEDED")
        print("="*80)
        print(f"OpenAI determined this doesn't need research.")
        print(f"Reason: {detection.get('reason')}")
        print("\n💡 This is expected for:")
        print("   • Meeting notes")
        print("   • Simple status updates")
        print("   • Already-resolved issues")
        print("\nTry selecting a different message that needs research.")
        return
    
    # STEP 2: Query Building
    print("\n" + "="*80)
    print("🔍 STEP 2: BUILDING SEARCH QUERY (Natural Language)")
    print("="*80)
    print("Converting message to a searchable question...")
    start = datetime.now()
    
    query = await exa.build_search_query(
        selected,
        detection.get('research_type', 'technical_comparison')
    )
    
    elapsed = (datetime.now() - start).total_seconds()
    print(f"\n✅ Generated Query ({elapsed:.1f}s):")
    print(f"   \"{query}\"")
    
    # STEP 3: Exa Search (with built-in summaries!)
    print("\n" + "="*80)
    print("🌐 STEP 3: EXA search_and_contents() - SINGLE API CALL")
    print("="*80)
    print(f"Query: \"{query}\"")
    print("(Exa will return results + content + AI summaries in one call!)")
    start = datetime.now()
    
    # Build summary prompt based on research type
    research_type = detection.get('research_type', 'technical_comparison')
    summary_prompts = {
        "technical_comparison": "Summarize the key technical differences and tradeoffs.",
        "best_practices": "Summarize the recommended best practices.",
        "competitive_analysis": "Summarize the competitive positioning.",
        "market_research": "Summarize the market trends."
    }
    summary_prompt = summary_prompts.get(research_type, summary_prompts["technical_comparison"])
    print(f"Summary prompt: \"{summary_prompt}\"")
    
    try:
        sources = await exa.search_with_contents(
            query=query, 
            num_results=5,
            summary_prompt=summary_prompt
        )
        elapsed = (datetime.now() - start).total_seconds()
        
        print(f"\n✅ Found {len(sources)} sources ({elapsed:.1f}s):")
        
        if sources:
            for i, source in enumerate(sources, 1):
                title = source.get('title', 'Untitled')[:70]
                url = source.get('url', 'N/A')
                summary = source.get('summary', '')
                has_summary = "✅" if summary else "❌"
                
                print(f"\n  📄 Source {i}: {title}")
                print(f"     🔗 {url}")
                print(f"     📝 Summary: {has_summary}")
                if summary:
                    print(f"     {summary[:200]}...")
        else:
            print("\n  ⚠️  No sources found!")
            print("\n  Possible causes:")
            print("   • Query too specific")
            print("   • Exa rate limit")
            print("   • Topic too niche")
            
    except Exception as e:
        print(f"\n❌ Exa search failed: {e}")
        import traceback
        traceback.print_exc()
        sources = []
    
    # STEP 4: Synthesize + Format for Jira
    if sources:
        print("\n" + "="*80)
        print("🧠 STEP 4: SYNTHESIZE & FORMAT FOR JIRA")
        print("="*80)
        print("OpenAI synthesizes findings → unified recommendation")
        print("Then formats with Exa source summaries as evidence")
        start = datetime.now()
        
        try:
            # Use the new format_research_for_jira method (now async with synthesis)
            research_type = detection.get('research_type', 'technical_comparison')
            summary = await exa.format_research_for_jira(query, sources, research_type)
            elapsed = (datetime.now() - start).total_seconds()
            
            if summary:
                print(f"\n✅ Synthesized output ({elapsed:.1f}s, {len(summary)} chars):")
                print("-" * 80)
                # Show full summary up to 1500 chars
                if len(summary) > 1500:
                    print(summary[:1500] + "\n...[truncated]...")
                else:
                    print(summary)
                print("-" * 80)
            else:
                print("\n⚠️  No output generated")
                
        except Exception as e:
            print(f"\n❌ Synthesis/formatting failed: {e}")
            import traceback
            traceback.print_exc()
            summary = None
    else:
        summary = None
    
    # FINAL EVALUATION
    print("\n" + "="*80)
    print("💡 EVALUATION SUMMARY")
    print("="*80)
    
    issues = []
    successes = []
    
    # Detection
    if detection.get('needs_research'):
        successes.append(f"✅ Correctly identified as needing {detection.get('research_type')} research")
    else:
        issues.append("⚠️ Marked as not needing research")
    
    # Query
    if query and len(query) > 10:
        successes.append(f"✅ Generated search query: \"{query[:50]}...\"")
    else:
        issues.append("⚠️ Query was too short or empty")
    
    # Sources
    if sources and len(sources) >= 3:
        successes.append(f"✅ Found {len(sources)} relevant sources")
    elif sources:
        issues.append(f"⚠️ Only found {len(sources)} sources (ideally 3+)")
    else:
        issues.append("❌ No sources found - query may be too specific")
    
    # Summary
    if summary and len(summary) > 200:
        successes.append(f"✅ Generated comprehensive summary ({len(summary)} chars)")
    elif summary:
        issues.append(f"⚠️ Summary is short ({len(summary)} chars)")
    else:
        issues.append("❌ No summary generated")
    
    print("\n📊 Results:")
    for s in successes:
        print(f"   {s}")
    for i in issues:
        print(f"   {i}")
    
    # Recommendations
    print("\n🎯 Recommendations:")
    if not sources:
        print("   • Try a more general search query")
        print("   • Check if Exa API key is valid and has credits")
        print("   • Try a different message with clearer technical terms")
    elif len(sources) < 3:
        print("   • The query might be too specific")
        print("   • Consider broadening the search terms")
    elif summary and len(summary) > 500:
        print("   • Research pipeline is working well!")
        print("   • Ready to create Jira tickets with enriched context")
    
    print()


if __name__ == "__main__":
    asyncio.run(main())

