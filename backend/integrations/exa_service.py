"""
Exa search service for intelligent ticket research.
Detects ticket types and searches for relevant solutions, documentation, and context.

ARCHITECTURE (v2 - Optimized):
1. detect_ticket_type() - LLM classifies message, determines if research needed
2. build_search_query() - LLM converts message to natural language search question
3. search_with_contents() - SINGLE Exa call with built-in summary generation
4. Format results for Jira - No additional LLM call needed!

Key optimizations:
- Uses search_and_contents() instead of search() + get_contents()
- Exa generates summaries via summary_query (no slow OpenAI summary step)
- Natural language queries instead of keyword stuffing
- No codebase injection in queries (was polluting results)
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from openai import OpenAI

from ..config import settings
from ..services.context_service import ContextService

logger = logging.getLogger(__name__)

# Exa Configuration
EXA_SEARCH_TYPE = "deep"           # "auto", "neural", "keyword" - auto lets Exa decide
EXA_LIVECRAWL = "always"           # "preferred", "always", "never" - always for fresh results
EXA_MAX_CHARACTERS = 1000          # Max content length per result
EXA_DAYS_LOOKBACK = 180            # Search last 6 months


class ExaSearchService:
    """Exa-powered research service for Jira tickets"""
    
    def __init__(self):
        """Initialize Exa and OpenAI clients"""
        self.exa_client = None
        self.openai_client = None
        self.context_service = ContextService()
        
        # Initialize Exa
        if settings.EXA_API_KEY:
            try:
                from exa_py import Exa
                self.exa_client = Exa(api_key=settings.EXA_API_KEY)
                logger.info("✅ Exa client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Exa client: {e}")
        else:
            logger.warning("EXA_API_KEY not set")
        
        # Initialize OpenAI for LLM detection and query building
        if settings.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("✅ OpenAI client initialized")
        else:
            logger.warning("OPENAI_API_KEY not set")
    
    async def detect_ticket_type(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM to detect ticket type and determine if research would be valuable.
        Uses light context (identity only) for speed.
        """
        if not self.openai_client:
            return {
                "ticket_type": "general_task",
                "needs_research": False,
                "research_type": "none",
                "reason": "OpenAI client not available"
            }
        
        message_text = message.get('text', '')[:500]
        
        prompt = f"""Analyze this Slack message. Determine the ticket type and if it requires web research.

Message: {message_text}
Channel: #{message.get('channel_name', 'unknown')}
Sender: {message.get('user_name', 'unknown')}

RULES:
- needs_research=true ONLY when ALL of these are true:
  1. There's a SPECIFIC question or task that can be answered with external research
  2. The question is about external topics (tools, frameworks, industry practices)
  3. The message has enough context to form a meaningful search query
  
  Examples where needs_research=true:
  • "Should we use Pinecone vs pgvector for our vector DB?" (specific tech comparison)
  • "What's the best practice for rate limiting APIs?" (specific best practice)
  
- needs_research=false for:
  • Bug reports (use internal code analysis instead)
  • Status updates, meeting notes, simple tasks
  • Vague internal discussions 

Respond with ONLY valid JSON (no markdown):
{{
  "ticket_type": "bug|feature_request|product_decision|customer_issue|general_task|meeting_note",
  "needs_research": true/false,
  "research_type": "technical_comparison|best_practices|competitive_analysis|market_research|none",
  "reason": "brief explanation"
}}"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a Product Manager. Classify messages and determine research needs."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=200
            )
            
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            result = json.loads(content)
            logger.info(f"✅ Detected ticket type: {result.get('ticket_type')} (research: {result.get('needs_research')})")
            return result
            
        except Exception as e:
            logger.error(f"Error detecting ticket type: {e}")
            return {"ticket_type": "general_task", "needs_research": False, "research_type": "none", "reason": f"Error: {e}"}
    
    async def build_search_query(self, message: Dict[str, Any], research_type: str) -> str:
        """
        Convert message to a natural language search question.
        
        NO codebase injection - just reformulates the user's question clearly.
        Exa uses semantic search, so natural language works better than keywords.
        """
        if not self.openai_client:
            # Fallback: use message text directly
            return message.get('text', '')[:200]
        
        message_text = message.get('text', '')[:400]
        
        prompt = f"""Reformulate this Slack message as a clear, searchable question.

Message: "{message_text}"
Research Type: {research_type}

RULES:
1. Write a complete natural language QUESTION (not keywords!)
2. Include specific technologies/products mentioned
3. Make it clear what kind of answer is needed
4. Keep it under 30 words
5. Do NOT add generic terms like "best practices" unless specifically asked

EXAMPLES (for format, not exhaustive):

Comparisons:
- "The data team is asking about event tracking. Mixpanel vs Amplitude - any quick takes?"
  → "What are the tradeoffs between Mixpanel and Amplitude for SaaS event tracking?"

Open-ended exploration:
- "Someone mentioned feature flags. Worth looking into?"
  → "What are the benefits of feature flags and when should a startup adopt them?"

Uncertainty/gaps:
- "Legal is asking about GDPR again. I think we're compliant but not sure what we're missing"
  → "What are the key GDPR compliance requirements for a SaaS application handling user data?"

Yes/no with implications:
- "Customer just asked if we support webhooks. Do we? Should we?"
  → "What are best practices for implementing webhook support in a SaaS product?"

Strategy questions:
- "Users keep asking for a mobile app. Not sure if we should do native or just improve the responsive site"
  → "What factors should determine whether to build a native mobile app vs improving mobile web experience?"

Vendor/tool evaluation:
- "Sales is pushing for Salesforce integration. How complex is this typically?"
  → "What is the typical complexity and timeline for building a Salesforce CRM integration?"

NOTE: These examples show the transformation style. If the message doesn't fit these patterns, use your best judgment to create a clear, searchable question. The goal is a natural language question that would return useful web results.

Your question (ONLY the question, no explanation):"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=100
            )
            query = response.choices[0].message.content.strip().strip('"')
            logger.info(f"🔍 Generated search query: {query}")
            return query
        except Exception as e:
            logger.error(f"Error building query: {e}")
            # Fallback
            return message_text

    async def search_with_contents(
        self, 
        query: str, 
        num_results: int = 5,
        summary_prompt: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform Exa search with contents AND summaries in a single call.
        
        This is the key optimization:
        - OLD: search() + get_contents() + OpenAI summary = 230 seconds
        - NEW: search_and_contents() with summary_query = 5-10 seconds
        
        Exa generates the summaries for us!
        """
        if not self.exa_client:
            logger.warning("Exa client not available")
            return []
        
        try:
            logger.info(f"🔍 Exa search_and_contents: {query[:80]}...")
            
            # Calculate date range
            start_date = (datetime.now() - timedelta(days=EXA_DAYS_LOOKBACK)).strftime("%Y-%m-%d")
            
            # Default summary prompt if not provided
            if not summary_prompt:
                summary_prompt = "Summarize the key points relevant to a software engineering team making a technical decision."
            
            # Build search parameters
            search_params = {
                "query": query,
                "num_results": num_results,
                "type": EXA_SEARCH_TYPE,
                "start_published_date": start_date,
                "text": {"max_characters": EXA_MAX_CHARACTERS},
                "summary": {"query": summary_prompt},
            }
            
            # Add livecrawl if supported (may not be in all Exa versions)
            try:
                search_params["livecrawl"] = EXA_LIVECRAWL
            except:
                pass
            
            # SINGLE API CALL - gets results, content, AND summaries
            response = self.exa_client.search_and_contents(**search_params)
            
            if not hasattr(response, 'results') or not response.results:
                logger.info("🔍 No results found")
                return []
            
            # Extract results with Exa-generated summaries
            enriched_results = []
            for result in response.results:
                enriched_results.append({
                    "title": getattr(result, 'title', 'Untitled'),
                    "url": getattr(result, 'url', ''),
                    "text": getattr(result, 'text', '')[:EXA_MAX_CHARACTERS],
                    "summary": getattr(result, 'summary', ''),  # Exa-generated summary!
                    "published_date": getattr(result, 'published_date', None),
                    "author": getattr(result, 'author', None),
                })
            
            logger.info(f"✅ Found {len(enriched_results)} results with summaries")
            return enriched_results
            
        except Exception as e:
            logger.error(f"Error in Exa search: {e}")
            return []
    
    async def synthesize_research(
        self, 
        query: str, 
        sources: List[Dict[str, Any]],
        research_type: str = "technical_comparison"
    ) -> str:
        """
        Synthesize Exa summaries into a unified recommendation.
        
        This adds ~2-3 seconds but provides:
        - Unified analysis across sources
        - Gap-filling with OpenAI's knowledge
        - Tailored recommendation
        
        Cost: ~$0.0003 (500 tokens)
        """
        if not self.openai_client or not sources:
            return ""
        
        # Combine Exa summaries (full) and full text for all 5 sources
        source_content = []
        for i, s in enumerate(sources[:5], 1):
            title = s.get('title', 'Source')
            summary = s.get('summary', '')  # Full summary, no truncation
            text = s.get('text', '')  # Full text (up to 1000 chars from Exa)
            
            content = f"### Source {i}: {title}\n"
            content += f"**Summary:** {summary}\n"
            if text:
                content += f"**Full Content:** {text}\n"
            source_content.append(content)
        
        combined_sources = "\n".join(source_content)
        
        # Tailor prompt based on research type
        type_guidance = {
            "technical_comparison": "Focus on technical tradeoffs and which option fits best for a Python/FastAPI stack.",
            "best_practices": "Focus on actionable recommendations and common pitfalls to avoid.",
            "competitive_analysis": "Focus on key differentiators and market positioning.",
            "market_research": "Focus on trends, statistics, and strategic implications."
        }
        guidance = type_guidance.get(research_type, type_guidance["technical_comparison"])
        
        prompt = f"""Based on these research findings, provide a brief synthesis and recommendation.

**Question:** {query}

**Research Sources (with full content):**
{combined_sources}

**Your Task:** {guidance}

**Format your response as:**
## 🎯 Synthesis & Recommendation

**Key Consensus:** [2-3 sentences summarizing what the sources agree on]

**Recommendation:** [2-3 sentences with your specific recommendation]

**Key Tradeoff:** [1 sentence on the main tradeoff to consider]

Keep the total response under 200 words. Be specific and actionable."""

        try:
            logger.info("🧠 Synthesizing research findings...")
            response = self.openai_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You are a senior technical advisor. Provide concise, actionable recommendations based on research findings."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            synthesis = response.choices[0].message.content.strip()
            logger.info("✅ Research synthesis complete")
            return synthesis
            
        except Exception as e:
            logger.error(f"Error synthesizing research: {e}")
            return ""
    
    async def format_research_for_jira(
        self, 
        query: str,
        sources: List[Dict[str, Any]],
        research_type: str = "technical_comparison"
    ) -> str:
        """
        Format Exa results into Jira-ready markdown WITH synthesis.
        
        Structure:
        1. Synthesis & Recommendation (OpenAI - unified analysis)
        2. Research Sources (Exa summaries - supporting evidence)
        """
        if not sources:
            return "No research results found."
        
        parts = []
        
        # 1. Add synthesis/recommendation at the top
        synthesis = await self.synthesize_research(query, sources, research_type)
        if synthesis:
            parts.append(synthesis)
            parts.append("\n---\n")
        
        # 2. Add source summaries as supporting evidence
        parts.append("## 📚 Research Sources\n")
        parts.append(f"*Query: {query}*\n")
        
        for i, source in enumerate(sources, 1):
            title = source.get('title', 'Untitled')
            url = source.get('url', '')
            summary = source.get('summary', source.get('text', '')[:300])
            published = source.get('published_date', '')
            
            parts.append(f"### {i}. {title}")
            if published:
                parts.append(f"*Published: {published}*\n")
            parts.append(f"{summary}\n")
            parts.append(f"[Read more]({url})\n")
        
        return "\n".join(parts)

    async def research_for_ticket(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrates the research workflow.
        
        Flow:
        1. Detect ticket type
        2. Route bugs to CodeBugAnalyzer
        3. Route research questions to Exa
        4. Format results for Jira
        """
        # 1. Detect ticket type
        detection = await self.detect_ticket_type(message)
        ticket_type = detection.get('ticket_type', 'general_task')
        
        # 2. Route bugs to CodeBugAnalyzer
        if ticket_type in ['bug', 'technical_error']:
            logger.info(f"🐛 Routing to CodeBugAnalyzer for ticket type: {ticket_type}")
            
            from ..services.code_bug_analyzer import CodeBugAnalyzer
            analyzer = CodeBugAnalyzer()
            code_analysis = await analyzer.analyze(message)
            
            return {
                "detection": detection,
                "analysis_type": "code_bug",
                "code_analysis": code_analysis,
                "sources": [],
                "research_summary": self._format_bug_analysis_summary(code_analysis)
            }
        
        # 3. Use Exa for research-style questions
        sources = []
        summary = None
        query = None
        research_type = detection.get('research_type', 'technical_comparison')
        
        if detection.get('needs_research'):
            logger.info(f"🔍 Routing to Exa research for ticket type: {ticket_type}")
            
            # Build natural language query
            query = await self.build_search_query(message, research_type)
            
            # Build a summary prompt based on research type
            summary_prompts = {
                "technical_comparison": "Summarize the key technical differences and tradeoffs for an engineering team.",
                "best_practices": "Summarize the recommended best practices and implementation tips.",
                "competitive_analysis": "Summarize the competitive positioning and key differentiators.",
                "market_research": "Summarize the market trends and relevant statistics."
            }
            summary_prompt = summary_prompts.get(research_type, summary_prompts["technical_comparison"])
            
            # Search with Exa-generated summaries
            sources = await self.search_with_contents(
                query=query,
                num_results=5,
                summary_prompt=summary_prompt
            )
            
            # Format for Jira WITH synthesis (adds unified recommendation)
            if sources:
                summary = await self.format_research_for_jira(query, sources, research_type)
        
        return {
            "detection": detection,
            "analysis_type": "exa_research",
            "query": query,
            "sources": sources,
            "research_summary": summary
        }
    
    def _format_bug_analysis_summary(self, code_analysis: Dict[str, Any]) -> str:
        """Format bug analysis results as a readable summary."""
        parts = []
        
        # Header
        parts.append("## 🐛 Code Bug Analysis\n")
        
        # Patterns detected
        patterns = code_analysis.get("patterns", {})
        if patterns.get("exception_types") or patterns.get("status_codes"):
            parts.append("### Detected Issues")
            if patterns.get("exception_types"):
                parts.append(f"- **Exception Types:** {', '.join(patterns['exception_types'])}")
            if patterns.get("status_codes"):
                parts.append(f"- **HTTP Status Codes:** {', '.join(patterns['status_codes'])}")
            parts.append("")
        
        # Affected files
        codebase_matches = code_analysis.get("codebase_matches", [])
        if codebase_matches:
            parts.append("### 📁 Affected Files")
            for match in codebase_matches[:5]:
                file_ref = f"`{match['file']}`"
                if match.get('line'):
                    file_ref += f" (line {match['line']})"
                parts.append(f"- {file_ref}")
                if match.get('snippet'):
                    parts.append(f"  ```\n  {match['snippet']}\n  ```")
            parts.append("")
        
        # Past similar issues
        memory_matches = code_analysis.get("memory_matches", [])
        if memory_matches:
            parts.append("### 🧠 Related Past Issues")
            for match in memory_matches[:3]:
                parts.append(f"- **{match['issue']}** (relevance: {match['relevance']})")
                if match.get('solution'):
                    solution = match['solution'][:200] + "..." if len(match['solution']) > 200 else match['solution']
                    parts.append(f"  - Solution: {solution}")
            parts.append("")
        
        # Debugging steps
        debugging_steps = code_analysis.get("debugging_steps", [])
        if debugging_steps:
            parts.append("### 🔧 Recommended Debugging Steps")
            for i, step in enumerate(debugging_steps, 1):
                parts.append(f"{i}. {step}")
            parts.append("")
        
        return "\n".join(parts)
