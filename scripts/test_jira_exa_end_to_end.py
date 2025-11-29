#!/usr/bin/env python3
"""
End-to-End Test: Jira Ticket Creation with Exa Research

Tests the full pipeline:
1. Select a high-priority message
2. Run Exa research
3. Create Jira ticket with research
4. Evaluate research quality
5. Display ticket URL

This provides complete visibility into the Jira + Exa integration.
"""

import sys
import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

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


class ResearchQualityEvaluator:
    """Evaluates the quality of Exa research results"""
    
    @staticmethod
    def evaluate_sources(sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate source quality"""
        if not sources:
            return {
                "score": 0,
                "grade": "F",
                "issues": ["No sources found"],
                "strengths": [],
                "source_count": 0,
                "domain_diversity": 0,
                "avg_content_length": 0
            }
        
        issues = []
        strengths = []
        score = 0
        
        # Check quantity (0-30 points)
        if len(sources) >= 5:
            score += 30
            strengths.append(f"Good source quantity ({len(sources)} sources)")
        elif len(sources) >= 3:
            score += 20
            strengths.append(f"Adequate sources ({len(sources)} sources)")
        else:
            score += 10
            issues.append(f"Limited sources ({len(sources)} only)")
        
        # Check source diversity (0-30 points)
        domains = set()
        for source in sources:
            url = source.get('url', '')
            if url:
                domain = url.split('/')[2] if len(url.split('/')) > 2 else 'unknown'
                domains.add(domain)
        
        if len(domains) >= 4:
            score += 30
            strengths.append(f"Diverse sources ({len(domains)} different domains)")
        elif len(domains) >= 2:
            score += 20
        else:
            score += 10
            issues.append("Limited source diversity (same domain)")
        
        # Check content length (0-20 points)
        if len(sources) > 0:
            avg_length = sum(len(s.get('text', '')) for s in sources) / len(sources)
            if avg_length >= 500:
                score += 20
                strengths.append("Detailed source content")
            elif avg_length >= 200:
                score += 15
            else:
                score += 5
                issues.append("Shallow source content")
        else:
            avg_length = 0
            issues.append("No content to evaluate")
        
        # Check for quality indicators (0-20 points)
        quality_indicators = 0
        for source in sources:
            title = source.get('title', '').lower()
            text = source.get('text', '').lower()
            url = source.get('url', '').lower()
            
            # Positive indicators
            if any(domain in url for domain in ['github.com', 'stackoverflow.com', 'medium.com', 'dev.to']):
                quality_indicators += 1
            if any(keyword in title or keyword in text for keyword in ['tutorial', 'guide', 'best practices', 'production']):
                quality_indicators += 1
        
        if quality_indicators >= 3:
            score += 20
            strengths.append("High-quality technical sources")
        elif quality_indicators >= 1:
            score += 10
        else:
            issues.append("Few authoritative sources")
        
        # Grade
        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 70:
            grade = "C"
        elif score >= 60:
            grade = "D"
        else:
            grade = "F"
        
        return {
            "score": score,
            "grade": grade,
            "issues": issues,
            "strengths": strengths,
            "source_count": len(sources),
            "domain_diversity": len(domains),
            "avg_content_length": int(avg_length)
        }
    
    @staticmethod
    def evaluate_summary(summary: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate research summary quality"""
        if not summary:
            return {
                "score": 0,
                "grade": "F",
                "issues": ["No summary generated"],
                "strengths": [],
                "length": 0,
                "cited_sources": 0,
                "technical_terms": 0
            }
        
        issues = []
        strengths = []
        score = 0
        
        # Check length (0-25 points)
        if len(summary) >= 800:
            score += 25
            strengths.append(f"Comprehensive summary ({len(summary)} chars)")
        elif len(summary) >= 400:
            score += 15
        else:
            score += 5
            issues.append(f"Brief summary ({len(summary)} chars)")
        
        # Check structure (0-25 points)
        has_sections = any(marker in summary for marker in ['##', '**', '1.', '2.', '- '])
        has_context = 'context' in summary.lower() or 'analysis' in summary.lower()
        has_recommendations = 'recommend' in summary.lower() or 'solution' in summary.lower()
        
        structure_score = 0
        if has_sections:
            structure_score += 10
            strengths.append("Well-structured with sections")
        if has_context:
            structure_score += 7
        if has_recommendations:
            structure_score += 8
            strengths.append("Includes actionable recommendations")
        
        if structure_score < 10:
            issues.append("Poorly structured summary")
        score += structure_score
        
        # Check source integration (0-25 points)
        source_urls = [s.get('url', '') for s in sources if s.get('url')]
        cited_urls = sum(1 for url in source_urls if url in summary or url.split('/')[2] in summary)
        
        if cited_urls >= 3:
            score += 25
            strengths.append(f"Good source citation ({cited_urls} sources referenced)")
        elif cited_urls >= 1:
            score += 15
        else:
            score += 5
            issues.append("Few source citations")
        
        # Check technical depth (0-25 points)
        technical_terms = ['api', 'database', 'async', 'cache', 'authentication', 
                          'endpoint', 'middleware', 'configuration', 'deployment',
                          'integration', 'python', 'fastapi', 'websocket']
        
        term_count = sum(1 for term in technical_terms if term in summary.lower())
        
        if term_count >= 5:
            score += 25
            strengths.append("Technical depth with specific terminology")
        elif term_count >= 3:
            score += 15
        else:
            score += 5
            issues.append("Lacks technical specificity")
        
        # Grade
        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 70:
            grade = "C"
        elif score >= 60:
            grade = "D"
        else:
            grade = "F"
        
        return {
            "score": score,
            "grade": grade,
            "issues": issues,
            "strengths": strengths,
            "length": len(summary),
            "cited_sources": cited_urls,
            "technical_terms": term_count
        }


async def main():
    """Run end-to-end Jira + Exa test"""
    print("\n" + "="*80)
    print("🧪 END-TO-END TEST: JIRA + EXA RESEARCH")
    print("="*80)
    
    # Check configuration
    if not settings.JIRA_SYNC_ENABLED:
        print("\n❌ Jira not enabled in .env (JIRA_SYNC_ENABLED=false)")
        sys.exit(1)
    
    if not settings.EXA_API_KEY:
        print("\n❌ EXA_API_KEY not set in .env")
        sys.exit(1)
    
    # Parse command line args
    message_index = 0  # Default to first message
    for arg in sys.argv[1:]:
        if arg.startswith("--message="):
            try:
                message_index = int(arg.split("=")[1]) - 1  # Convert 1-based to 0-based
            except:
                print(f"\n⚠️  Invalid message index: {arg}")
                pass
    
    # Initialize services
    inbox = InboxService()
    jira = JiraService()
    exa = ExaSearchService()
    evaluator = ResearchQualityEvaluator()
    
    print(f"\n✅ Connected to Jira: {jira.base_url}")
    print(f"   Project: {jira.project_key}")
    
    # Fetch high-priority messages
    print("\n📬 Fetching high-priority messages...")
    high_priority = await inbox.get_all(hours_ago=168, limit=50)  # Get more messages
    
    if not high_priority:
        print("\n❌ No high-priority messages found")
        print("   Run 'python scripts/sync_once.py' to fetch messages")
        sys.exit(0)
    
    # Display messages
    print(f"\n📋 Found {len(high_priority)} high-priority messages:")
    print("-" * 80)
    
    for i, msg in enumerate(high_priority[:5], 1):
        score = msg['priority_score']
        user = msg['user_name']
        channel = msg['channel_name']
        text = msg['text'][:60].replace('\n', ' ')
        
        emoji = "🔴" if score >= 90 else "🟡" if score >= 75 else "🟢"
        
        marker = "👉" if i == 1 else "  "
        print(f"{marker} {emoji} {i}. [{score:3d}] {user} in #{channel}")
        print(f"      {text}...")
    
    print("-" * 80)
    
    # Select message (default to first, or use --message=N)
    if message_index >= len(high_priority):
        print(f"\n⚠️  Message index {message_index + 1} out of range, using first message")
        message_index = 0
    
    selected_msg = high_priority[message_index]
    
    print("\n" + "="*80)
    print("📝 SELECTED MESSAGE:")
    print("="*80)
    print(f"From: {selected_msg['user_name']} in #{selected_msg['channel_name']}")
    print(f"Priority: {selected_msg['priority_score']}/100")
    print(f"\nMessage:\n{selected_msg['text'][:300]}...")
    print("="*80)
    
    # Run research
    print("\n🔍 Running Exa research...")
    start_time = datetime.now()
    
    research = await exa.research_for_ticket(selected_msg)
    
    research_time = (datetime.now() - start_time).total_seconds()
    
    detection = research.get('detection', {})
    sources = research.get('sources', [])
    summary = research.get('research_summary', '')
    analysis_type = research.get('analysis_type', 'unknown')
    
    print(f"   ✅ Research completed in {research_time:.1f}s")
    print(f"   📊 Type: {detection.get('ticket_type', 'unknown')}")
    print(f"   🔬 Analysis: {analysis_type}")
    
    # Evaluate research quality
    print("\n" + "="*80)
    print("📊 RESEARCH QUALITY EVALUATION")
    print("="*80)
    
    if analysis_type == 'code_bug':
        # Bug analysis evaluation
        code_analysis = research.get('code_analysis', {})
        patterns = code_analysis.get('patterns', {})
        
        print("\n🐛 Code Bug Analysis:")
        print(f"   Exceptions: {patterns.get('exception_types', [])}")
        print(f"   Files: {patterns.get('file_mentions', [])}")
        print(f"   Codebase Matches: {len(code_analysis.get('codebase_matches', []))}")
        print(f"   Memory Matches: {len(code_analysis.get('memory_matches', []))}")
        print(f"   Debugging Steps: {len(code_analysis.get('debugging_steps', []))}")
        
        # Simple scoring for bug analysis
        bug_score = 0
        if patterns.get('exception_types'):
            bug_score += 25
        if code_analysis.get('codebase_matches'):
            bug_score += 25
        if code_analysis.get('memory_matches'):
            bug_score += 25
        if len(code_analysis.get('debugging_steps', [])) >= 3:
            bug_score += 25
        
        bug_grade = "A" if bug_score >= 90 else "B" if bug_score >= 80 else "C" if bug_score >= 70 else "D" if bug_score >= 60 else "F"
        
        print(f"\n   📈 Bug Analysis Score: {bug_score}/100 ({bug_grade})")
        
    else:
        # Exa research evaluation
        print("\n🔬 Evaluating Sources...")
        source_eval = evaluator.evaluate_sources(sources)
        
        print(f"\n   📚 Source Quality: {source_eval['score']}/100 ({source_eval['grade']})")
        print(f"      • Sources found: {source_eval['source_count']}")
        print(f"      • Domain diversity: {source_eval['domain_diversity']} unique domains")
        print(f"      • Avg content length: {source_eval['avg_content_length']} chars")
        
        if source_eval['strengths']:
            print("\n   ✅ Strengths:")
            for strength in source_eval['strengths']:
                print(f"      • {strength}")
        
        if source_eval['issues']:
            print("\n   ⚠️  Issues:")
            for issue in source_eval['issues']:
                print(f"      • {issue}")
        
        # Show top sources
        if sources:
            print(f"\n   📖 Top Sources:")
            for i, source in enumerate(sources[:3], 1):
                print(f"      {i}. {source.get('title', 'Untitled')[:60]}...")
                print(f"         {source.get('url', 'N/A')}")
        
        print("\n🔬 Evaluating Summary...")
        summary_eval = evaluator.evaluate_summary(summary, sources)
        
        print(f"\n   📝 Summary Quality: {summary_eval['score']}/100 ({summary_eval['grade']})")
        print(f"      • Length: {summary_eval['length']} chars")
        print(f"      • Sources cited: {summary_eval['cited_sources']}")
        print(f"      • Technical terms: {summary_eval['technical_terms']}")
        
        if summary_eval['strengths']:
            print("\n   ✅ Strengths:")
            for strength in summary_eval['strengths']:
                print(f"      • {strength}")
        
        if summary_eval['issues']:
            print("\n   ⚠️  Issues:")
            for issue in summary_eval['issues']:
                print(f"      • {issue}")
        
        # Overall grade
        overall_score = (source_eval['score'] + summary_eval['score']) / 2
        overall_grade = "A" if overall_score >= 90 else "B" if overall_score >= 80 else "C" if overall_score >= 70 else "D" if overall_score >= 60 else "F"
        
        print(f"\n   🎯 Overall Research Quality: {overall_score:.0f}/100 ({overall_grade})")
    
    # Create Jira ticket
    print("\n" + "="*80)
    print("🎫 CREATING JIRA TICKET")
    print("="*80)
    
    summary_text = selected_msg['text'][:100]
    issue_type = jira._determine_issue_type(detection.get('ticket_type', 'general_task'), selected_msg['text'])
    
    code_analysis = research.get('code_analysis') if analysis_type == 'code_bug' else None
    research_summary = summary if analysis_type != 'code_bug' else research.get('research_summary')
    
    print(f"\n   Summary: {summary_text}")
    print(f"   Type: {issue_type}")
    print(f"   Research: {'Yes (CodeBugAnalyzer)' if code_analysis else 'Yes (Exa)' if research_summary else 'No'}")
    
    try:
        result = await jira.create_ticket(
            message=selected_msg,
            summary=summary_text,
            issue_type=issue_type,
            research_summary=research_summary,
            code_analysis=code_analysis,
            ticket_type=detection.get('ticket_type')
        )
        
        ticket_key = result.get('jira_key')
        ticket_url = result.get('jira_url')
        
        print(f"\n   ✅ Ticket created: {ticket_key}")
        print(f"   🔗 URL: {ticket_url}")
        
    except Exception as e:
        print(f"\n   ❌ Failed to create ticket: {e}")
        logger.exception("Ticket creation failed")
        sys.exit(1)
    
    # Save test results
    output_dir = Path(__file__).parent.parent / "simulations"
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = output_dir / f"jira_exa_test_{timestamp}.json"
    
    test_results = {
        "timestamp": timestamp,
        "message": {
            "text": selected_msg['text'],
            "user": selected_msg['user_name'],
            "channel": selected_msg['channel_name'],
            "priority_score": selected_msg['priority_score']
        },
        "research": {
            "type": analysis_type,
            "ticket_type": detection.get('ticket_type'),
            "research_time_seconds": research_time,
            "sources_count": len(sources)
        },
        "quality": {
            "source_evaluation": source_eval if analysis_type != 'code_bug' else None,
            "summary_evaluation": summary_eval if analysis_type != 'code_bug' else None,
        },
        "jira_ticket": {
            "key": ticket_key,
            "url": ticket_url,
            "issue_type": issue_type
        }
    }
    
    with open(output_file, 'w') as f:
        json.dump(test_results, f, indent=2)
    
    # Final summary
    print("\n" + "="*80)
    print("✅ TEST COMPLETE")
    print("="*80)
    print(f"\n📊 Summary:")
    print(f"   • Research time: {research_time:.1f}s")
    print(f"   • Analysis type: {analysis_type}")
    print(f"   • Jira ticket: {ticket_key}")
    print(f"   • Results saved: {output_file}")
    
    print(f"\n🔗 Next Steps:")
    print(f"   1. Open Jira ticket: {ticket_url}")
    print(f"   2. Verify research formatting looks good")
    print(f"   3. Check if context is actionable")
    print(f"   4. Review test results: {output_file}")
    print()


if __name__ == "__main__":
    asyncio.run(main())

