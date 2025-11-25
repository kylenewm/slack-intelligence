"""
Exa search service for intelligent ticket research.
Detects ticket types and searches for relevant solutions, documentation, and context.
ENHANCED: Uses ContextService to inject Traverse.ai awareness into the research process.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from openai import OpenAI

from ..config import settings
from ..services.context_service import ContextService

logger = logging.getLogger(__name__)


class ExaSearchService:
    """Exa-powered research service for Jira tickets"""
    
    def __init__(self):
        """Initialize Exa and OpenAI clients, plus Context Engine"""
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
        
        # Initialize OpenAI for LLM detection and formatting
        if settings.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("✅ OpenAI client initialized")
        else:
            logger.warning("OPENAI_API_KEY not set")
    
    async def detect_ticket_type(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM to detect ticket type and determine if research would be valuable.
        Injects Traverse.ai context to filter out irrelevant noise.
        """
        if not self.openai_client:
            return {
                "ticket_type": "general_task",
                "needs_research": False,
                "research_type": "none",
                "reason": "OpenAI client not available"
            }
        
        # Get Traverse.ai Context (RAG + Static)
        message_text = message.get('text', '')[:500]
        full_context = await self.context_service.get_full_context(query=message_text)
        
        prompt = f"""Analyze this Slack message. Determine if it is relevant to Traverse.ai's product (Slack Middleware) and if it requires external research.

{full_context}

Message: {message.get('text', '')[:500]}
Channel: #{message.get('channel_name', 'unknown')}
Sender: {message.get('user_name', 'unknown')}
Priority Score: {message.get('priority_score', 0)}/100

Respond with ONLY valid JSON (no markdown):
{{
  "ticket_type": "bug|feature_request|product_decision|customer_issue|general_task|meeting_note",
  "needs_research": true/false,
  "research_type": "technical_solution|market_research|competitive_analysis|best_practices|none",
  "reason": "brief explanation relating to Traverse.ai context"
}}"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a Product Manager at Traverse.ai. Classify messages strictly based on their relevance to our Slack Middleware platform."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
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
    
    async def build_search_query(self, message: Dict[str, Any], ticket_type: str, research_type: str) -> str:
        """
        Build a context-aware search query using Traverse.ai's tech stack.
        """
        message_text = message.get('text', '')[:300]
        
        # Get just the codebase structure for query refinement
        codebase_map = self.context_service._scan_codebase()
        
        prompt = f"""Generate a specific Exa search query for this issue.
Use the Traverse.ai codebase structure to infer specific libraries/frameworks.

Codebase Structure:
{codebase_map}

Issue: "{message_text}"
Ticket Type: {ticket_type}
Research Type: {research_type}

Return ONLY the search query string. Do not include quotes or explanations.
Example: "fastapi sqlalchemy integrity error postgresql"
"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a Senior Engineer at Traverse.ai. Create highly technical, specific search queries based on our stack (Python/FastAPI/SQLAlchemy)."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=100
            )
            query = response.choices[0].message.content.strip().replace('"', '')
            logger.info(f"🔍 Generated Context-Aware Query: {query}")
            return query
        except Exception:
            # Fallback
            return f"python fastapi {message_text}"

    async def search_with_contents(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """
        Perform Exa search and fetch contents.
        """
        if not self.exa_client:
            logger.warning("Exa client not available")
            return []
        
        try:
            logger.info(f"🔍 Exa search: {query}...")
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            
            # 1. Search
            search_results = self.exa_client.search(
                query,
                num_results=num_results,
                start_published_date=start_date,
                use_autoprompt=True # Let Exa optimize the query too
            )
            
            if not hasattr(search_results, 'results') or not search_results.results:
                return []
            
            # 2. Get Contents
            result_ids = [r.id for r in search_results.results]
            contents = self.exa_client.get_contents(result_ids)
            
            enriched_results = []
            for i, result in enumerate(search_results.results):
                content_obj = contents.results[i] if i < len(contents.results) else None
                enriched_results.append({
                    "title": getattr(result, 'title', 'Untitled'),
                    "url": getattr(result, 'url', ''),
                    "text": getattr(content_obj, 'text', '')[:2000] if content_obj else '',
                    "author": getattr(result, 'author', None)
                })
            
            return enriched_results
            
        except Exception as e:
            logger.error(f"Error in Exa search: {e}")
            return []
    
    async def format_research_summary(
        self, 
        message: Dict[str, Any], 
        search_results: List[Dict[str, Any]],
        ticket_type: str
    ) -> Dict[str, str]:
        """
        Format results into a Traverse.ai engineering brief.
        """
        if not self.openai_client or not search_results:
            return {"summary": "No research available.", "plain_summary": ""}
        
        # Get context relevant to the message
        full_context = await self.context_service.get_full_context(query=message.get('text', ''))
        
        results_context = ""
        for i, result in enumerate(search_results[:5], 1):
            results_context += f"\n--- Source {i} ---\nTitle: {result['title']}\nURL: {result['url']}\nContent: {result['text'][:500]}...\n"
        
        prompt = f"""You are a Senior Engineer at Traverse.ai. Write a research note for this issue.

{full_context}

Issue: "{message.get('text', '')}"
Search Results:
{results_context}

Format as a Markdown engineering note:
## 🧠 Context Analysis
[Explain why this matters to Traverse.ai's platform. Reference specific files or past issues if relevant.]

## 📚 Key Findings
- [Bullet point 1 with link]
- [Bullet point 2 with link]

## 🛠️ Recommended Solution
[Technical recommendation based on our FastAPI/Python stack]
"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful, technical assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=800
            )
            
            summary = response.choices[0].message.content.strip()
            return {
                "summary": summary,
                "plain_summary": summary.replace("#", "").replace("**", "")
            }
            
        except Exception as e:
            logger.error(f"Error formatting summary: {e}")
            return {"summary": "Error formatting summary.", "plain_summary": ""}

    async def research_for_ticket(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrates the research workflow.
        """
        # 1. Detect
        detection = await self.detect_ticket_type(message)
        
        sources = []
        summary = None
        
        if detection.get('needs_research'):
            # 2. Build Query (Context-Aware)
            query = await self.build_search_query(
                message, 
                detection.get('ticket_type', 'general_task'),
                detection.get('research_type', 'none')
            )
            
            # 3. Search
            sources = await self.search_with_contents(query, num_results=5)
            
            # 4. Summarize (Context-Aware)
            if sources:
                formatted = await self.format_research_summary(
                    message,
                    sources,
                    detection.get('ticket_type', 'general_task')
                )
                summary = formatted.get('summary')
        
        return {
            "detection": detection,
            "sources": sources,
            "research_summary": summary
        }
