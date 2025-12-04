"""
Jira integration service for creating tickets from Slack messages.
"""

import logging
from typing import Dict, Any, Optional, List
import httpx
from slack_sdk.web.async_client import AsyncWebClient

from ..config import settings

logger = logging.getLogger(__name__)


def markdown_to_adf(markdown_text: str) -> List[Dict[str, Any]]:
    """
    Convert markdown text to Atlassian Document Format (ADF) content blocks.
    
    Handles:
    - ## Headers → heading blocks
    - **bold** → strong marks
    - `code` → code marks
    - - bullets → bulletList
    - [text](url) → links
    - Plain paragraphs
    """
    import re
    
    content = []
    lines = markdown_text.strip().split('\n')
    current_list_items = []
    
    def flush_list():
        """Add accumulated list items as a bulletList"""
        nonlocal current_list_items
        if current_list_items:
            content.append({
                "type": "bulletList",
                "content": current_list_items
            })
            current_list_items = []
    
    def parse_inline(text: str) -> List[Dict[str, Any]]:
        """Parse inline formatting (bold, code, links) into ADF marks"""
        result = []
        
        # Pattern for **bold**, `code`, and [text](url)
        pattern = r'(\*\*([^*]+)\*\*)|(`([^`]+)`)|(\[([^\]]+)\]\(([^)]+)\))'
        
        last_end = 0
        for match in re.finditer(pattern, text):
            # Add plain text before this match
            if match.start() > last_end:
                plain = text[last_end:match.start()]
                if plain:
                    result.append({"type": "text", "text": plain})
            
            if match.group(2):  # **bold**
                result.append({
                    "type": "text",
                    "text": match.group(2),
                    "marks": [{"type": "strong"}]
                })
            elif match.group(4):  # `code`
                result.append({
                    "type": "text",
                    "text": match.group(4),
                    "marks": [{"type": "code"}]
                })
            elif match.group(6):  # [text](url)
                result.append({
                    "type": "text",
                    "text": match.group(6),
                    "marks": [{"type": "link", "attrs": {"href": match.group(7)}}]
                })
            
            last_end = match.end()
        
        # Add remaining plain text
        if last_end < len(text):
            remaining = text[last_end:]
            if remaining:
                result.append({"type": "text", "text": remaining})
        
        # If no formatting found, return simple text
        if not result and text:
            result = [{"type": "text", "text": text}]
        
        return result
    
    for line in lines:
        line = line.strip()
        
        if not line:
            flush_list()
            continue
        
        # ## Header
        if line.startswith('## '):
            flush_list()
            header_text = line[3:].strip()
            # Remove emoji if present at start
            content.append({
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": header_text}]
            })
        
        # ### Subheader
        elif line.startswith('### '):
            flush_list()
            header_text = line[4:].strip()
            content.append({
                "type": "heading",
                "attrs": {"level": 3},
                "content": [{"type": "text", "text": header_text}]
            })
        
        # --- Horizontal rule
        elif line == '---':
            flush_list()
            content.append({"type": "rule"})
        
        # - Bullet point
        elif line.startswith('- ') or line.startswith('* '):
            bullet_text = line[2:].strip()
            current_list_items.append({
                "type": "listItem",
                "content": [{
                    "type": "paragraph",
                    "content": parse_inline(bullet_text)
                }]
            })
        
        # Numbered list (1. 2. etc)
        elif re.match(r'^\d+\.\s', line):
            flush_list()
            item_text = re.sub(r'^\d+\.\s*', '', line)
            content.append({
                "type": "paragraph",
                "content": parse_inline(item_text)
            })
        
        # Regular paragraph
        else:
            flush_list()
            if line.startswith('*') and line.endswith('*') and not line.startswith('**'):
                # Italic text (entire line)
                content.append({
                    "type": "paragraph",
                    "content": [{
                        "type": "text",
                        "text": line.strip('*'),
                        "marks": [{"type": "em"}]
                    }]
                })
            else:
                content.append({
                    "type": "paragraph",
                    "content": parse_inline(line)
                })
    
    flush_list()
    return content


class JiraService:
    """Jira API client for ticket management"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        email: Optional[str] = None,
        domain: Optional[str] = None,
        project_key: Optional[str] = None
    ):
        """
        Initialize Jira client.
        
        Args:
            api_key: Jira API token (defaults to settings.JIRA_API_KEY)
            email: Jira email address (defaults to settings.JIRA_EMAIL)
            domain: Jira domain like "your-company" (defaults to settings.JIRA_DOMAIN)
            project_key: Jira project key like "PROJ" (defaults to settings.JIRA_PROJECT_KEY)
        """
        self.api_key = api_key or settings.JIRA_API_KEY
        self.email = email or settings.JIRA_EMAIL
        self.domain = domain or settings.JIRA_DOMAIN
        self.project_key = project_key or settings.JIRA_PROJECT_KEY
        self.slack_client = AsyncWebClient(token=settings.SLACK_BOT_TOKEN)
        
        if not self.api_key or not self.domain or not self.project_key or not self.email:
            logger.warning("Jira credentials not fully configured")
            self.enabled = False
        else:
            self.enabled = True
            self.base_url = f"https://{self.domain}.atlassian.net"
            
            # Create Basic Auth string
            import base64
            auth_str = f"{self.email}:{self.api_key}"
            self.auth_header = f"Basic {base64.b64encode(auth_str.encode()).decode()}"
            
            logger.info(f"✅ Jira client initialized for {self.base_url}")
    
    def _map_priority(self, priority_score: int) -> str:
        """
        Map Slack priority score to Jira priority.
        
        Args:
            priority_score: Score from 0-100
            
        Returns:
            Jira priority name (Highest, High, Medium, Low)
        """
        if priority_score >= 90:
            return "Highest"
        elif priority_score >= 75:
            return "High"
        elif priority_score >= 50:
            return "Medium"
        else:
            return "Low"
    
    def _determine_issue_type(self, ticket_type: str, message_text: str) -> str:
        """
        Determine Jira issue type based on ticket type.
        
        Args:
            ticket_type: Detected ticket type from Exa service
            message_text: Original message text
            
        Returns:
            Jira issue type (Bug, Task, Story, Epic)
        """
        if ticket_type in ["bug", "technical_error"]:
            return "Bug"
        elif ticket_type == "feature_request":
            return "Story"
        elif "epic" in message_text.lower() or "initiative" in message_text.lower():
            return "Epic"
        else:
            return "Task"
    
    async def _enrich_context(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich message context with thread history and related messages.
        
        Args:
            message: Slack message dict
            
        Returns:
            Dict with thread_context and related_messages
        """
        enriched = {
            "thread_context": None,
            "related_messages": []
        }
        
        try:
            # Get thread context if message is part of a thread
            thread_ts = message.get('thread_ts')
            channel_id = message.get('channel_id')
            
            if thread_ts and channel_id:
                logger.info("📝 Fetching thread context...")
                
                # Fetch thread replies
                response = await self.slack_client.conversations_replies(
                    channel=channel_id,
                    ts=thread_ts,
                    limit=20
                )
                
                if response.get('ok') and response.get('messages'):
                    thread_messages = response['messages']
                    
                    # Format thread summary
                    thread_summary = []
                    for msg in thread_messages[:10]:  # Limit to 10 messages
                        user = msg.get('user', 'Unknown')
                        text = msg.get('text', '')
                        thread_summary.append(f"{user}: {text[:200]}")
                    
                    enriched['thread_context'] = {
                        'message_count': len(thread_messages),
                        'summary': "\n".join(thread_summary)
                    }
                    
                    logger.info(f"✅ Found {len(thread_messages)} thread messages")
            
            # Could also add: search for related messages in same channel by keywords
            # For now, keeping it simple with just thread context
            
        except Exception as e:
            logger.warning(f"⚠️  Failed to enrich context: {e}")
        
        return enriched
    
    def _format_description(
        self, 
        message: Dict[str, Any],
        research_summary: Optional[str] = None,
        context_enrichment: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format Jira ticket description with message, research, and context using ADF.
        
        Args:
            message: Slack message dict
            research_summary: Optional Exa research summary
            context_enrichment: Optional enriched context (thread history, related messages)
            
        Returns:
            Atlassian Document Format (ADF) dict
        """
        # Build ADF content blocks
        content = [
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Original Slack Message"}]
            },
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "From: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": f"{message.get('user_name', 'Unknown')} in #{message.get('channel_name', 'unknown')}"}
                ]
            },
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Priority: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": f"{message.get('priority_score', 0)}/100 - {message.get('priority_reason', 'N/A')}"}
                ]
            },
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Time: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": f"{message.get('timestamp', 'Unknown')}"}
                ]
            },
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": message.get('text', 'No message text')}]
            }
        ]
        
        # Add Slack link if available
        if message.get('link'):
            content.append({
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "View in Slack",
                        "marks": [{"type": "link", "attrs": {"href": message.get('link')}}]
                    }
                ]
            })
        
        content.append({"type": "rule"})
        
        # Add thread context if available
        if context_enrichment and context_enrichment.get('thread_context'):
            thread_ctx = context_enrichment['thread_context']
            content.extend([
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": f"💬 Thread Context ({thread_ctx['message_count']} messages)"}]
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": thread_ctx['summary'][:2000]}]  # Limit length
                },
                {"type": "rule"}
            ])
        
        # Add research summary if present (convert markdown to ADF)
        if research_summary:
            content.append({
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "🔍 Research & Recommendation"}]
            })
            
            # Convert markdown research to proper ADF formatting
            research_adf = markdown_to_adf(research_summary[:4000])
            content.extend(research_adf)
            
            content.append({"type": "rule"})
        
        # Add next steps
        content.extend([
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Next Steps"}]
            },
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Review the message context and research findings to determine the best course of action."}]
            }
        ])
        
        return {
            "version": 1,
            "type": "doc",
            "content": content
        }
    
    def _format_bug_analysis_description(
        self,
        message: Dict[str, Any],
        code_analysis: Dict[str, Any],
        context_enrichment: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format bug analysis specifically for Jira using ADF.
        Shows PM summary at top for quick understanding, then engineer details.
        """
        content = []
        
        # PM Summary at the top (high-level understanding)
        pm_summary = code_analysis.get("pm_summary", code_analysis.get("summary", ""))
        if pm_summary:
            content.extend([
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "📋 Summary"}]
                },
                {
                    "type": "panel",
                    "attrs": {"panelType": "info"},
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": pm_summary}]
                        }
                    ]
                },
                {"type": "rule"}
            ])
        
        # Original Slack Message
        content.extend([
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "💬 Original Report"}]
            },
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "From: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": f"{message.get('user_name', 'Unknown')} in #{message.get('channel_name', 'unknown')}"}
                ]
            },
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": message.get('text', 'No message text')}]
            },
            {"type": "rule"}
        ])
        
        # Engineer Context Section
        engineer_context = code_analysis.get("engineer_context", {})
        patterns = engineer_context.get("patterns", code_analysis.get("patterns", {}))
        
        # Detected Patterns
        if patterns.get("exception_types") or patterns.get("status_codes"):
            content.append({
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "🔍 Technical Details"}]
            })
            
            pattern_text = []
            if patterns.get("exception_types"):
                pattern_text.append(f"Exceptions: {', '.join(patterns['exception_types'])}")
            if patterns.get("status_codes"):
                pattern_text.append(f"HTTP Errors: {', '.join(patterns['status_codes'])}")
            if patterns.get("likely_cause"):
                pattern_text.append(f"Likely cause: {patterns['likely_cause']}")
            
            content.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": " | ".join(pattern_text)}]
            })
        
        # Affected Files
        affected_files = engineer_context.get("affected_files", [])
        codebase_matches = engineer_context.get("codebase_matches", code_analysis.get("codebase_matches", []))
        
        if affected_files or codebase_matches:
            content.append({
                "type": "heading",
                "attrs": {"level": 3},
                "content": [{"type": "text", "text": "📁 Affected Files"}]
            })
            
            # Show unique files
            shown_files = set()
            for match in codebase_matches[:5]:
                file_path = match.get('file', '')
                if file_path and file_path not in shown_files:
                    shown_files.add(file_path)
                    file_text = file_path
                    if match.get('line'):
                        file_text += f" (line {match['line']})"
                    
                    content.append({
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": "• "},
                            {"type": "text", "text": file_text, "marks": [{"type": "code"}]}
                        ]
                    })
            
            content.append({"type": "rule"})
        
        # Past Solutions (most valuable for engineers)
        past_solutions = engineer_context.get("past_solutions", [])
        memory_matches = code_analysis.get("memory_matches", [])
        solutions_to_show = past_solutions if past_solutions else memory_matches
        
        if solutions_to_show:
            content.append({
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "🧠 Past Solutions"}]
            })
            
            for match in solutions_to_show[:3]:
                # Issue title with relevance
                relevance = match.get('relevance', 0)
                relevance_text = f" ({relevance:.0%} match)" if relevance else ""
                
                content.append({
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": match.get('issue', 'Unknown'), "marks": [{"type": "strong"}]},
                        {"type": "text", "text": relevance_text}
                    ]
                })
                
                # Solution in a panel for visibility
                solution = match.get('solution', '')
                if solution:
                    solution_text = solution[:500] + "..." if len(solution) > 500 else solution
                    content.append({
                        "type": "panel",
                        "attrs": {"panelType": "success"},
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": solution_text}]
                            }
                        ]
                    })
        
        return {
            "version": 1,
            "type": "doc",
            "content": content
        }
    
    async def create_ticket(
        self,
        message: Dict[str, Any],
        summary: Optional[str] = None,
        description: Optional[str] = None,
        issue_type: Optional[str] = None,
        priority: Optional[str] = None,
        assignee: Optional[str] = None,
        labels: Optional[list] = None,
        research_summary: Optional[str] = None,
        ticket_type: Optional[str] = None,
        code_analysis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a Jira ticket from a Slack message.
        
        Args:
            message: Slack message dict
            summary: Ticket summary (defaults to first 100 chars of message)
            description: Ticket description (defaults to formatted message + research)
            issue_type: Jira issue type (Bug, Task, Story, Epic)
            priority: Jira priority (Highest, High, Medium, Low)
            assignee: Email of assignee (optional)
            labels: List of labels (optional)
            research_summary: Exa research summary (optional)
            ticket_type: Detected ticket type (optional)
            code_analysis: Code bug analysis results (optional, for bugs)
            
        Returns:
            Dict with jira_key, jira_url, success status
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "Jira not configured",
                "jira_key": None,
                "jira_url": None
            }
        
        try:
            # Enrich context with thread history (make await self._enrich_context(message) to add back in)
            context_enrichment = None
            
            # Build ticket data
            ticket_summary = summary or message.get('text', '')[:100]
            
            # Handle description - convert to ADF if plain text
            if description and isinstance(description, str):
                # Convert plain text to ADF format
                ticket_description = {
                    "version": 1,
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}]
                        }
                    ]
                }
            elif description and isinstance(description, dict):
                # Already in ADF format
                ticket_description = description
            elif code_analysis:
                # Use bug analysis formatter for code bugs
                ticket_description = self._format_bug_analysis_description(
                    message,
                    code_analysis,
                    context_enrichment
                )
            else:
                # Use formatted description with message + research
                ticket_description = self._format_description(
                message, 
                research_summary,
                context_enrichment
            )
            ticket_issue_type = issue_type or self._determine_issue_type(
                ticket_type or "general_task",
                message.get('text', '')
            )
            ticket_priority = priority or self._map_priority(message.get('priority_score', 50))
            
            # Build labels
            ticket_labels = labels or []
            ticket_labels.extend([
                "slack-intelligence",
                f"channel-{message.get('channel_name', 'unknown')}"
            ])
            
            # Build Jira API payload
            payload = {
                "fields": {
                    "project": {
                        "key": self.project_key
                    },
                    "summary": ticket_summary,
                    "description": ticket_description,
                    "issuetype": {
                        "name": ticket_issue_type
                    },
                    "priority": {
                        "name": ticket_priority
                    },
                    "labels": ticket_labels
                }
            }
            
            # Add assignee if provided
            if assignee:
                payload["fields"]["assignee"] = {
                    "emailAddress": assignee
                }
            
            # Make API request
            headers = {
                "Authorization": self.auth_header,
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"Creating Jira ticket in project {self.project_key}...")
                response = await client.post(
                    f"{self.base_url}/rest/api/3/issue",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    jira_key = result.get('key')
                    jira_url = f"{self.base_url}/browse/{jira_key}"
                    
                    logger.info(f"✅ Created Jira ticket: {jira_key}")
                    
                    return {
                        "success": True,
                        "jira_key": jira_key,
                        "jira_url": jira_url,
                        "jira_id": result.get('id')
                    }
                else:
                    error_msg = f"Jira API error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "jira_key": None,
                        "jira_url": None
                    }
                    
        except Exception as e:
            error_msg = f"Error creating Jira ticket: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "jira_key": None,
                "jira_url": None
            }
    
    async def get_ticket(self, jira_key: str) -> Optional[Dict[str, Any]]:
        """
        Get ticket details from Jira.
        
        Args:
            jira_key: Jira ticket key (e.g., PROJ-123)
            
        Returns:
            Dict with ticket details or None if not found
        """
        if not self.enabled:
            logger.warning("Jira not configured")
            return None
        
        try:
            headers = {
                "Authorization": self.auth_header,
                "Accept": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/rest/api/3/issue/{jira_key}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to get Jira ticket {jira_key}: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting Jira ticket: {e}")
            return None




