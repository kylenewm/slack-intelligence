"""
Comprehensive Context Engine Test Script

Tests the context engine with various edge cases and provides detailed
visibility into the full process (not just inputs/outputs).

Features:
1. Multiple test scenarios (easy, medium, hard, edge cases)
2. Full process visibility (context assembly, query building, research, synthesis)
3. Edge cases that require context to answer well (not spoonfed)
4. Detailed logging of each step
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.tree import Tree

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.context_service import ContextService
from backend.integrations.exa_service import ExaSearchService
from backend.config import settings

console = Console()

class ContextEngineTester:
    """Comprehensive tester for the context engine"""
    
    def __init__(self):
        self.context_service = ContextService()
        self.exa_service = ExaSearchService()
        self.results = []
        
    def print_section(self, title: str, content: str = ""):
        """Print a formatted section header"""
        console.print(f"\n[bold cyan]{'='*80}[/bold cyan]")
        console.print(f"[bold cyan]{title}[/bold cyan]")
        console.print(f"[bold cyan]{'='*80}[/bold cyan]")
        if content:
            console.print(content)
    
    def print_step(self, step_num: int, title: str, content: Any = None):
        """Print a numbered step with optional content"""
        console.print(f"\n[bold yellow]Step {step_num}:[/bold yellow] [bold]{title}[/bold]")
        if content:
            if isinstance(content, str):
                console.print(content)
            elif isinstance(content, dict):
                console.print(json.dumps(content, indent=2))
            else:
                console.print(str(content))
    
    async def test_context_assembly(self, query: Optional[str] = None) -> Dict[str, Any]:
        """Test and display full context assembly"""
        self.print_section("🧠 CONTEXT ASSEMBLY TEST")
        
        console.print("[dim]Assembling full context...[/dim]")
        full_context = await self.context_service.get_full_context(query=query)
        
        # Break down context into components
        context_parts = {
            "Identity": None,
            "Institutional Memory": None,
            "Product Plans": None,
            "Codebase Structure": None,
            "Team Context": None
        }
        
        current_section = None
        current_content = []
        
        for line in full_context.split('\n'):
            if line.startswith('=== COMPANY IDENTITY ==='):
                if current_section:
                    context_parts[current_section] = '\n'.join(current_content)
                current_section = "Identity"
                current_content = []
            elif line.startswith('=== INSTITUTIONAL MEMORY'):
                if current_section:
                    context_parts[current_section] = '\n'.join(current_content)
                current_section = "Institutional Memory"
                current_content = []
            elif line.startswith('=== PRODUCT PLANS'):
                if current_section:
                    context_parts[current_section] = '\n'.join(current_content)
                current_section = "Product Plans"
                current_content = []
            elif line.startswith('=== CODEBASE STRUCTURE'):
                if current_section:
                    context_parts[current_section] = '\n'.join(current_content)
                current_section = "Codebase Structure"
                current_content = []
            elif line.startswith('=== TEAM CONTEXT ==='):
                if current_section:
                    context_parts[current_section] = '\n'.join(current_content)
                current_section = "Team Context"
                current_content = []
            elif current_section and line.strip():
                current_content.append(line)
        
        if current_section:
            context_parts[current_section] = '\n'.join(current_content)
        
        # Display each component
        for component, content in context_parts.items():
            if content:
                self.print_step(0, f"{component} Component", "")
                # Truncate for display
                preview = content[:500] + "..." if len(content) > 500 else content
                console.print(Panel(preview, title=component, border_style="blue"))
        
        # Show context stats
        stats_table = Table(title="Context Statistics")
        stats_table.add_column("Component", style="cyan")
        stats_table.add_column("Size (chars)", style="green")
        stats_table.add_column("Lines", style="yellow")
        
        for component, content in context_parts.items():
            if content:
                stats_table.add_row(
                    component,
                    str(len(content)),
                    str(len(content.split('\n')))
                )
        
        console.print(stats_table)
        
        return {
            "full_context": full_context,
            "components": context_parts,
            "total_size": len(full_context)
        }
    
    async def test_query(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Test a single query through the full pipeline"""
        self.print_section(f"🧪 TEST CASE: {test_case['name']}")
        
        message = test_case['message']
        expected_context_usage = test_case.get('expected_context_usage', [])
        difficulty = test_case.get('difficulty', 'medium')
        
        console.print(f"[bold]Difficulty:[/bold] {difficulty}")
        console.print(f"[bold]Message:[/bold] {message['text']}")
        console.print(f"[bold]Expected Context Usage:[/bold] {', '.join(expected_context_usage) if expected_context_usage else 'None specified'}")
        
        result = {
            "test_name": test_case['name'],
            "message": message,
            "steps": {},
            "analysis_type": "unknown"
        }
        
        # Step 1: Context Assembly
        self.print_step(1, "Context Assembly")
        context_result = await self.test_context_assembly(query=message['text'])
        result['steps']['context_assembly'] = context_result
        
        # Step 2: Ticket Type Detection
        self.print_step(2, "Ticket Type Detection")
        detection = await self.exa_service.detect_ticket_type(message)
        result['steps']['detection'] = detection
        
        detection_table = Table(title="Detection Results")
        detection_table.add_column("Field", style="cyan")
        detection_table.add_column("Value", style="green")
        for key, value in detection.items():
            detection_table.add_row(key, str(value))
        console.print(detection_table)
        
        # Step 2.5: Route to CodeBugAnalyzer if it's a bug
        code_analysis = None
        if detection.get('ticket_type') in ['bug', 'technical_error']:
            result['analysis_type'] = 'code_bug'
            self.print_step(2.5, "CodeBugAnalyzer Analysis")
            console.print("[dim]Routing to CodeBugAnalyzer for bug analysis...[/dim]")
            
            from backend.services.code_bug_analyzer import CodeBugAnalyzer
            analyzer = CodeBugAnalyzer()
            code_analysis = await analyzer.analyze(message)
            result['steps']['code_analysis'] = code_analysis
            
            # Display code analysis results
            if code_analysis:
                # Memory matches
                memory_matches = code_analysis.get('memory_matches', [])
                if memory_matches:
                    console.print(f"[bold green]Found {len(memory_matches)} institutional memory matches[/bold green]")
                    memory_table = Table(title="Institutional Memory Matches")
                    memory_table.add_column("#", style="cyan")
                    memory_table.add_column("Issue", style="green")
                    memory_table.add_column("Relevance", style="yellow")
                    memory_table.add_column("Solution Preview", style="blue")
                    
                    for i, match in enumerate(memory_matches[:3], 1):
                        issue = match.get('issue', '')[:50]
                        relevance = f"{match.get('relevance', 0):.2f}"
                        solution = match.get('solution', '')[:60] + "..." if len(match.get('solution', '')) > 60 else match.get('solution', '')
                        memory_table.add_row(str(i), issue, relevance, solution)
                    
                    console.print(memory_table)
                else:
                    console.print("[yellow]No institutional memory matches found[/yellow]")
                
                # Codebase matches
                codebase_matches = code_analysis.get('codebase_matches', [])
                if codebase_matches:
                    console.print(f"[bold green]Found {len(codebase_matches)} codebase matches[/bold green]")
                    codebase_table = Table(title="Codebase Matches")
                    codebase_table.add_column("#", style="cyan")
                    codebase_table.add_column("File", style="green")
                    codebase_table.add_column("Line", style="yellow")
                    codebase_table.add_column("Match Type", style="blue")
                    
                    for i, match in enumerate(codebase_matches[:5], 1):
                        file = match.get('file', '')[:40]
                        line = str(match.get('line', 'N/A'))
                        match_type = match.get('match_type', 'unknown')
                        codebase_table.add_row(str(i), file, line, match_type)
                    
                    console.print(codebase_table)
                else:
                    console.print("[yellow]No codebase matches found[/yellow]")
        
        # Step 3: Query Building (if research needed)
        if detection.get('needs_research'):
            result['analysis_type'] = 'exa_research'
            self.print_step(3, "Search Query Building")
            research_type = detection.get('research_type', 'technical_comparison')
            if not research_type or research_type == 'none':
                research_type = 'technical_comparison'
            query = await self.exa_service.build_search_query(
                message,
                research_type
            )
            result['steps']['query'] = query
            
            console.print(f"[bold green]Generated Query:[/bold green] {query}")
            
            # Analyze query quality
            query_analysis = self._analyze_query_quality(query, message['text'], context_result)
            result['steps']['query_analysis'] = query_analysis
            
            query_table = Table(title="Query Quality Analysis")
            query_table.add_column("Metric", style="cyan")
            query_table.add_column("Value", style="green")
            query_table.add_column("Status", style="yellow")
            
            for metric, (value, status) in query_analysis.items():
                status_emoji = "✅" if status == "good" else "⚠️" if status == "warning" else "❌"
                query_table.add_row(metric, str(value), f"{status_emoji} {status}")
            
            console.print(query_table)
            
            # Step 4: Research (if Exa is available)
            if self.exa_service.exa_client:
                self.print_step(4, "Exa Research")
                console.print("[dim]Performing Exa search...[/dim]")
                
                research_type = detection.get('research_type', 'technical_comparison')
                summary_prompts = {
                    "technical_comparison": "Summarize the key technical differences and tradeoffs for an engineering team.",
                    "best_practices": "Summarize the recommended best practices and implementation tips.",
                    "competitive_analysis": "Summarize the competitive positioning and key differentiators.",
                    "market_research": "Summarize the market trends and relevant statistics."
                }
                summary_prompt = summary_prompts.get(research_type, summary_prompts["technical_comparison"])
                
                sources = await self.exa_service.search_with_contents(
                    query=query,
                    num_results=5,
                    summary_prompt=summary_prompt
                )
                result['steps']['sources'] = sources
                
                if sources:
                    console.print(f"[bold green]Found {len(sources)} sources[/bold green]")
                    
                    # Compact table for overview with quality indicators
                    sources_table = Table(title="Research Sources Overview")
                    sources_table.add_column("#", style="cyan", width=3)
                    sources_table.add_column("Title", style="green", width=45)
                    sources_table.add_column("URL", style="blue", width=30)
                    sources_table.add_column("Summary", style="yellow", width=15)
                    sources_table.add_column("Quality", style="magenta", width=12)
                    
                    for i, source in enumerate(sources[:5], 1):
                        title = source.get('title', 'Untitled')
                        url = source.get('url', '')
                        summary = source.get('summary', '')
                        summary_len = len(summary)
                        word_count = len(summary.split()) if summary else 0
                        has_content = bool(source.get('text', ''))
                        
                        # Truncate for table
                        title_display = title[:42] + "..." if len(title) > 45 else title
                        url_display = url[:27] + "..." if len(url) > 30 else url
                        
                        # Quality assessment
                        if summary_len > 100 and word_count > 20 and has_content:
                            quality_score = "✅ Good"
                        elif summary_len > 0:
                            quality_score = "⚠️ Short"
                        else:
                            quality_score = "❌ None"
                        
                        sources_table.add_row(
                            str(i), 
                            title_display, 
                            url_display,
                            f"{summary_len} chars",
                            quality_score
                        )
                    
                    console.print(sources_table)
                    
                    # Detailed view for each source with quality analysis
                    console.print(f"\n[bold cyan]📄 Detailed Source Analysis:[/bold cyan]")
                    for i, source in enumerate(sources[:5], 1):
                        console.print(f"\n[bold yellow]{'='*80}[/bold yellow]")
                        console.print(f"[bold yellow]Source {i}/{len(sources)}:[/bold yellow]")
                        console.print(f"[bold]Title:[/bold] {source.get('title', 'Untitled')}")
                        console.print(f"[bold]URL:[/bold] {source.get('url', 'N/A')}")
                        
                        # Show full summary with quality metrics
                        summary = source.get('summary', '')
                        if summary:
                            word_count = len(summary.split())
                            sentences = summary.count('.') + summary.count('!') + summary.count('?')
                            console.print(f"\n[bold cyan]📝 Full Summary ({len(summary)} characters, {word_count} words, {sentences} sentences):[/bold cyan]")
                            console.print(Panel(
                                summary,
                                title=f"Source {i} Summary",
                                border_style="blue",
                                expand=False
                            ))
                            
                            # Quality indicators
                            quality_notes = []
                            if word_count < 20:
                                quality_notes.append("⚠️ Very short")
                            elif word_count > 200:
                                quality_notes.append("✅ Comprehensive")
                            if sentences < 2:
                                quality_notes.append("⚠️ Few sentences")
                            if 'recommended' in summary.lower() or 'should' in summary.lower() or 'best' in summary.lower():
                                quality_notes.append("✅ Actionable")
                            if word_count > 50 and sentences > 3:
                                quality_notes.append("✅ Well-structured")
                            
                            if quality_notes:
                                console.print(f"[dim]Quality: {' | '.join(quality_notes)}[/dim]")
                        else:
                            console.print("[yellow]⚠️ No summary available[/yellow]")
                        
                        # Show text content preview and compare to summary
                        text = source.get('text', '')
                        if text:
                            text_len = len(text)
                            text_preview = text[:400] + "..." if text_len > 400 else text
                            console.print(f"\n[bold cyan]📄 Content Preview ({text_len} characters):[/bold cyan]")
                            console.print(f"[dim]{text_preview}[/dim]")
                            
                            # Compare summary to content for alignment check
                            if summary:
                                summary_words = set(summary.lower().split()[:20])
                                content_words = set(text.lower().split()[:50])
                                overlap = len(summary_words & content_words)
                                coverage = (overlap / len(summary_words) * 100) if summary_words else 0
                                
                                if coverage > 50:
                                    console.print(f"[green]✅ Summary aligns with content ({coverage:.0f}% word overlap)[/green]")
                                elif coverage > 25:
                                    console.print(f"[yellow]⚠️ Moderate alignment ({coverage:.0f}% word overlap)[/yellow]")
                                else:
                                    console.print(f"[red]❌ Low alignment ({coverage:.0f}% word overlap)[/red]")
                        
                        # Metadata
                        metadata_parts = []
                        if source.get('published_date'):
                            metadata_parts.append(f"Published: {source.get('published_date')}")
                        if source.get('author'):
                            metadata_parts.append(f"Author: {source.get('author')}")
                        if metadata_parts:
                            console.print(f"[dim]{' | '.join(metadata_parts)}[/dim]")
                    
                    # Step 5: Synthesis
                    self.print_step(5, "Research Synthesis")
                    synthesis = await self.exa_service.synthesize_research(
                        query=query,
                        sources=sources,
                        research_type=research_type
                    )
                    result['steps']['synthesis'] = synthesis
                    
                    if synthesis:
                        console.print(Panel(Markdown(synthesis), title="Synthesis & Recommendation", border_style="green"))
                    else:
                        console.print("[yellow]No synthesis generated[/yellow]")
                    
                    # Step 6: Final Formatting
                    self.print_step(6, "Final Research Summary")
                    final_summary = await self.exa_service.format_research_for_jira(
                        query=query,
                        sources=sources,
                        research_type=research_type
                    )
                    result['steps']['final_summary'] = final_summary
                    
                    console.print(Panel(Markdown(final_summary[:1000] + "..." if len(final_summary) > 1000 else final_summary), 
                                      title="Final Research Summary", border_style="cyan"))
                else:
                    console.print("[yellow]No research sources found[/yellow]")
            else:
                console.print("[yellow]Exa client not available, skipping research step[/yellow]")
        else:
            console.print("[dim]Research not needed for this ticket type[/dim]")
        
        # Step 7: Context Usage Analysis
        self.print_step(7, "Context Usage Analysis")
        context_usage = self._analyze_context_usage(result, context_result, expected_context_usage)
        result['steps']['context_usage_analysis'] = context_usage
        
        usage_table = Table(title="Context Usage Analysis")
        usage_table.add_column("Expected Context", style="cyan")
        usage_table.add_column("Found", style="green")
        usage_table.add_column("Status", style="yellow")
        
        for expected in expected_context_usage:
            found = context_usage.get(expected, {}).get('found', False)
            details = context_usage.get(expected, {}).get('details', '')
            status_emoji = "✅" if found else "❌"
            usage_table.add_row(expected, "Yes" if found else "No", f"{status_emoji} {details}")
        
        console.print(usage_table)
        
        return result
    
    def _analyze_query_quality(self, query: str, original_message: str, context_result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the quality of the generated search query"""
        analysis = {}
        
        # Check if query is too generic
        generic_terms = ['best practices', 'how to', 'what is', 'guide']
        is_generic = any(term in query.lower() for term in generic_terms)
        analysis['Specificity'] = ("Generic" if is_generic else "Specific", "warning" if is_generic else "good")
        
        # Check if query mentions technologies from context
        codebase_context = context_result['components'].get('Codebase Structure', '')
        identity_context = context_result['components'].get('Identity', '')
        
        tech_terms = ['python', 'fastapi', 'slack', 'jira', 'notion', 'postgres', 'sqlite']
        mentioned_techs = [tech for tech in tech_terms if tech in query.lower()]
        analysis['Technology Context'] = (f"{len(mentioned_techs)} techs mentioned" if mentioned_techs else "No tech context", 
                                          "good" if mentioned_techs else "warning")
        
        # Check query length
        query_length = len(query.split())
        analysis['Query Length'] = (f"{query_length} words", 
                                   "good" if 5 <= query_length <= 30 else "warning")
        
        # Check if query is a question
        is_question = query.strip().endswith('?')
        analysis['Question Format'] = ("Question" if is_question else "Statement", 
                                       "good" if is_question else "warning")
        
        return analysis
    
    def _analyze_context_usage(self, result: Dict[str, Any], context_result: Dict[str, Any], 
                              expected: List[str]) -> Dict[str, Any]:
        """Analyze whether expected context components were used"""
        usage = {}
        
        context_components = context_result['components']
        detection = result['steps'].get('detection', {})
        analysis_type = result.get('analysis_type', 'unknown')
        
        # For bugs, check CodeBugAnalyzer output
        # For research, check Exa output
        if analysis_type == 'code_bug' or detection.get('ticket_type') in ['bug', 'technical_error']:
            code_analysis = result['steps'].get('code_analysis', {})
            memory_matches = code_analysis.get('memory_matches', [])
            codebase_matches = code_analysis.get('codebase_matches', [])
            
            for component in expected:
                found = False
                details = ""
                
                if component == "Institutional Memory":
                    found = len(memory_matches) > 0
                    if found:
                        top_match = memory_matches[0] if memory_matches else {}
                        issue = top_match.get('issue', '')
                        relevance = top_match.get('relevance', 0)
                        details = f"Found {len(memory_matches)} match(es) - top: {issue[:40]} (relevance: {relevance:.2f})"
                    else:
                        details = "No institutional memory matches found"
                
                elif component == "Codebase Structure":
                    found = len(codebase_matches) > 0
                    if found:
                        top_match = codebase_matches[0] if codebase_matches else {}
                        file = top_match.get('file', '')
                        details = f"Found {len(codebase_matches)} codebase match(es) - top: {file[:40]}"
                    else:
                        details = "No codebase matches found"
                
                elif component == "Identity":
                    # For bugs, identity might not be directly used
                    found = False
                    details = "Identity not typically used in bug analysis"
                
                elif component == "Product Plans":
                    # For bugs, product plans might not be directly used
                    found = False
                    details = "Product plans not typically used in bug analysis"
                
                usage[component] = {
                    "found": found,
                    "details": details
                }
        else:
            # For Exa research, check the research output
            query = result['steps'].get('query', '')
            synthesis = result['steps'].get('synthesis', '')
            final_summary = result['steps'].get('final_summary', '')
            
            all_text = f"{query} {synthesis} {final_summary}".lower()
            
            for component in expected:
                found = False
                details = ""
                
                if component == "Identity":
                    # Check if Traverse.ai or company-specific terms appear
                    identity_text = context_components.get('Identity', '').lower()
                    if identity_text:
                        company_terms = ['traverse', 'slack os', 'enterprise', 'engineering teams']
                        found = any(term in all_text for term in company_terms)
                        details = "Company identity terms found" if found else "No company identity terms"
                
                elif component == "Institutional Memory":
                    # For Exa research, institutional memory shouldn't be used (they removed it)
                    found = False
                    details = "Institutional memory not used in Exa queries (by design)"
                
                elif component == "Codebase Structure":
                    # For Exa research, codebase shouldn't be used (they removed it)
                    found = False
                    details = "Codebase structure not used in Exa queries (by design)"
                
                elif component == "Product Plans":
                    # Check if product plans are referenced
                    plans_text = context_components.get('Product Plans', '')
                    if plans_text:
                        # Look for plan-specific terms
                        plan_terms = ['conversation stitching', 'simulation testing', 'prd']
                        found = any(term in all_text for term in plan_terms)
                        details = "Product plans referenced" if found else "Product plans available but not referenced"
                    else:
                        found = False
                        details = "No product plans available"
                
                usage[component] = {
                    "found": found,
                    "details": details
                }
        
        return usage
    
    async def run_all_tests(self):
        """Run all test cases"""
        self.print_section("🚀 CONTEXT ENGINE COMPREHENSIVE TEST SUITE")
        
        # Define test cases
        test_cases = [
            {
                "name": "Easy: Generic Question (No Context Needed)",
                "difficulty": "easy",
                "message": {
                    "text": "What's the best way to handle API rate limiting?",
                    "channel_name": "engineering",
                    "user_name": "TestUser",
                    "priority_score": 50
                },
                "expected_context_usage": [],
                "description": "Generic question that doesn't need specific context"
            },
            {
                "name": "Medium: Context-Aware Question",
                "difficulty": "medium",
                "message": {
                    "text": "We're seeing 429 errors when fetching messages from Slack. What should we do?",
                    "channel_name": "engineering",
                    "user_name": "TestUser",
                    "priority_score": 80
                },
                "expected_context_usage": ["Institutional Memory", "Codebase Structure"],
                "description": "Question that should reference past solutions and codebase"
            },
            {
                "name": "Hard: Architecture Decision (Needs Full Context)",
                "difficulty": "hard",
                "message": {
                    "text": "Should we use OAuth or SAML for enterprise authentication? We need to integrate with existing enterprise systems.",
                    "channel_name": "product",
                    "user_name": "TestUser",
                    "priority_score": 90
                },
                "expected_context_usage": ["Identity", "Product Plans"],
                "description": "Architecture decision that needs company context and product plans"
            },
            {
                "name": "Edge Case: Ambiguous Question",
                "difficulty": "hard",
                "message": {
                    "text": "How do we handle this?",
                    "channel_name": "engineering",
                    "user_name": "TestUser",
                    "priority_score": 60
                },
                "expected_context_usage": ["Codebase Structure", "Institutional Memory"],
                "description": "Vague question that requires context to understand"
            },
            {
                "name": "Edge Case: Technology Comparison (Needs Stack Context)",
                "difficulty": "hard",
                "message": {
                    "text": "Should we use pgvector or Pinecone for vector search?",
                    "channel_name": "engineering",
                    "user_name": "TestUser",
                    "priority_score": 75
                },
                "expected_context_usage": ["Identity", "Codebase Structure"],
                "description": "Tech comparison that should consider our stack (Python/FastAPI)"
            },
            {
                "name": "Edge Case: Bug Report (Should Use Codebase Analysis)",
                "difficulty": "medium",
                "message": {
                    "text": "Getting errors when creating Jira tickets. The API is returning 400 Bad Request.",
                    "channel_name": "engineering",
                    "user_name": "TestUser",
                    "priority_score": 85
                },
                "expected_context_usage": ["Codebase Structure", "Institutional Memory"],
                "description": "Bug report that should trigger codebase analysis"
            },
            {
                "name": "Edge Case: Product Feature Question",
                "difficulty": "hard",
                "message": {
                    "text": "What's the status of the conversation stitching feature?",
                    "channel_name": "product",
                    "user_name": "TestUser",
                    "priority_score": 70
                },
                "expected_context_usage": ["Product Plans"],
                "description": "Question about product features should reference PRDs"
            }
        ]
        
        console.print(f"[bold]Running {len(test_cases)} test cases...[/bold]\n")
        
        for i, test_case in enumerate(test_cases, 1):
            console.print(f"\n[bold magenta]Test {i}/{len(test_cases)}[/bold magenta]")
            try:
                result = await self.test_query(test_case)
                self.results.append(result)
            except Exception as e:
                console.print(f"[bold red]Error in test case: {e}[/bold red]")
                import traceback
                console.print(traceback.format_exc())
                self.results.append({
                    "test_name": test_case['name'],
                    "error": str(e)
                })
        
        # Summary
        self.print_section("📊 TEST SUMMARY")
        self._print_summary()
        
        # Save results
        output_file = Path(__file__).parent.parent / "simulations" / f"context_engine_test_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        console.print(f"\n[bold green]Results saved to: {output_file}[/bold green]")
    
    def _print_summary(self):
        """Print test summary"""
        summary_table = Table(title="Test Results Summary")
        summary_table.add_column("Test Name", style="cyan")
        summary_table.add_column("Difficulty", style="yellow")
        summary_table.add_column("Research Needed", style="green")
        summary_table.add_column("Context Used", style="blue")
        summary_table.add_column("Status", style="magenta")
        
        for result in self.results:
            if 'error' in result:
                summary_table.add_row(
                    result.get('test_name', 'Unknown'),
                    "N/A",
                    "N/A",
                    "N/A",
                    f"❌ Error: {result['error']}"
                )
            else:
                detection = result.get('steps', {}).get('detection', {})
                needs_research = detection.get('needs_research', False)
                context_usage = result.get('steps', {}).get('context_usage_analysis', {})
                
                # Count how many expected contexts were found
                found_count = sum(1 for v in context_usage.values() if v.get('found', False))
                total_expected = len(context_usage)
                context_score = f"{found_count}/{total_expected}" if total_expected > 0 else "N/A"
                
                status = "✅" if (not total_expected or found_count == total_expected) else "⚠️"
                
                summary_table.add_row(
                    result.get('test_name', 'Unknown'),
                    "N/A",  # Could extract from test case
                    "Yes" if needs_research else "No",
                    context_score,
                    status
                )
        
        console.print(summary_table)


async def main():
    """Main entry point"""
    tester = ContextEngineTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[bold red]Warning: OPENAI_API_KEY not set. Some tests will be limited.[/bold red]")
    
    if not os.getenv("EXA_API_KEY"):
        console.print("[bold yellow]Warning: EXA_API_KEY not set. Research tests will be skipped.[/bold yellow]")
    
    asyncio.run(main())

