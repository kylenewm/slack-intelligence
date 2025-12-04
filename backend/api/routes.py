"""
FastAPI routes for Slack Intelligence API.
"""

import logging
from fastapi import APIRouter, HTTPException, Query, Form
from typing import List, Optional

logger = logging.getLogger(__name__)

from .schemas import (
    SmartInboxResponse,
    MessageDetail,
    SyncResponse,
    SearchResponse,
    StatsResponse
)
from ..services.inbox_service import InboxService
from ..services.sync_service import SyncService
from ..services.code_bug_analyzer import CodeBugAnalyzer
from ..integrations.exa_service import ExaSearchService
from ..integrations.jira_service import JiraService
from ..integrations.notion_service import NotionSyncService
from ..database.cache_service import CacheService
from ..config import settings

router = APIRouter(prefix="/api/slack", tags=["slack"])

# Initialize services
inbox_service = InboxService()
sync_service = SyncService()
exa_service = ExaSearchService()
jira_service = JiraService()
cache_service = CacheService()
bug_analyzer = CodeBugAnalyzer()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "slack-intelligence",
        "version": "1.0.0"
    }


@router.get("/inbox", response_model=SmartInboxResponse)
async def get_smart_inbox(
    view: str = Query(
        "all",
        description="Inbox view",
        enum=["all", "needs_response", "high_priority", "fyi", "low_priority"]
    ),
    hours_ago: int = Query(24, ge=1, le=168, description="Time window in hours"),
    limit: int = Query(50, ge=1, le=200, description="Max messages to return")
):
    """
    Get smart inbox with AI-prioritized messages.
    
    **Views:**
    - `all`: All messages sorted by priority
    - `needs_response`: Messages requiring your response (urgent)
    - `high_priority`: Important messages to read soon
    - `fyi`: Medium priority FYI messages
    - `low_priority`: Low priority / archived messages
    
    **Example:**
    ```
    GET /api/slack/inbox?view=needs_response&hours_ago=24&limit=20
    ```
    """
    try:
        if view == "needs_response":
            messages = await inbox_service.get_needs_response(hours_ago, limit)
        elif view == "high_priority":
            messages = await inbox_service.get_high_priority(hours_ago, limit)
        elif view == "fyi":
            messages = await inbox_service.get_fyi(hours_ago, limit)
        elif view == "low_priority":
            messages = await inbox_service.get_low_priority(hours_ago, limit)
        else:
            messages = await inbox_service.get_all(hours_ago, limit)
        
        from datetime import datetime, timezone
        return {
            "view": view,
            "total": len(messages),
            "messages": messages,
            "generated_at": datetime.now(timezone.utc)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync", response_model=SyncResponse)
async def sync_messages(
    channel_ids: Optional[List[str]] = Query(None, description="Specific channels to sync"),
    hours_ago: int = Query(24, ge=1, le=168, description="Hours to look back"),
    force: bool = Query(False, description="Re-process cached messages")
):
    """
    Manually trigger sync of Slack messages.
    
    Fetches new messages from Slack and prioritizes them with AI.
    
    **Example:**
    ```
    POST /api/slack/sync?hours_ago=24
    POST /api/slack/sync?channel_ids=C123&channel_ids=C456&hours_ago=12
    ```
    """
    try:
        result = await sync_service.sync(
            channel_ids=channel_ids,
            hours_ago=hours_ago,
            force=force
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """
    Get system statistics.
    
    Returns message counts by category and latest sync info.
    """
    try:
        stats = await inbox_service.get_stats()
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Slack Intelligence API",
        "version": "1.0.0",
        "description": "AI-powered Slack inbox prioritization and search",
        "endpoints": {
            "inbox": "/api/slack/inbox",
            "sync": "/api/slack/sync",
            "stats": "/api/slack/stats",
            "exa_detect": "/api/slack/integrations/exa/detect",
            "exa_research": "/api/slack/integrations/exa/research",
            "jira_create": "/api/slack/integrations/jira/create",
            "docs": "/docs"
        }
    }


# Exa and Jira Integration Endpoints

@router.post("/integrations/exa/detect")
async def detect_ticket_type(message_id: int):
    """
    Detect ticket type and determine if Exa research would be valuable.
    
    Args:
        message_id: Database ID of the Slack message
        
    Returns:
        Detection result with ticket_type, needs_research, research_type, reason
    """
    try:
        # Get message from database
        message = cache_service.get_message_by_id(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Convert to dict for exa_service
        message_dict = {
            "text": message.text,
            "channel_name": message.channel_name,
            "user_name": message.user_name,
            "priority_score": message.priority_score
        }
        
        # Detect ticket type
        detection = await exa_service.detect_ticket_type(message_dict)
        
        return {
            "message_id": message_id,
            "detection": detection
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/integrations/exa/research")
async def research_with_exa(message_id: int):
    """
    Perform Exa research for a Slack message.
    
    Args:
        message_id: Database ID of the Slack message
        
    Returns:
        Research summary and sources
    """
    try:
        # Get message from database
        message = cache_service.get_message_by_id(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Convert to dict for exa_service
        message_dict = {
            "text": message.text,
            "channel_name": message.channel_name,
            "user_name": message.user_name,
            "priority_score": message.priority_score
        }
        
        # Perform full research workflow
        result = await exa_service.research_for_ticket(message_dict)
        
        return {
            "message_id": message_id,
            "detection": result.get('detection'),
            "sources": result.get('sources', []),
            "research_summary": result.get('research_summary')
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/integrations/bug-analysis/{message_id}")
async def get_bug_analysis(message_id: int):
    """
    Get bug analysis for a Slack message.
    Shows full pipeline: detection → patterns → codebase matches → memory matches → debugging steps.
    
    Args:
        message_id: Database ID of the Slack message
        
    Returns:
        Full bug analysis including patterns, matches, and debugging steps
    """
    try:
        # Get message from database
        message = cache_service.get_message_by_id(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Convert to dict for bug analyzer
        message_dict = {
            "text": message.text,
            "channel_name": message.channel_name,
            "user_name": message.user_name,
            "priority_score": message.priority_score,
            "message_id": message.message_id,
            "channel_id": message.channel_id
        }
        
        # First check if it's a bug
        detection = await exa_service.detect_ticket_type(message_dict)
        ticket_type = detection.get('ticket_type', 'general_task')
        
        if ticket_type not in ['bug', 'technical_error']:
            return {
                "message_id": message_id,
                "is_bug": False,
                "detection": detection,
                "message": "This message is not classified as a bug. Use /integrations/exa/research for research."
            }
        
        # Run bug analysis
        code_analysis = await bug_analyzer.analyze(message_dict)
        
        # Format for Jira preview
        jira_preview = jira_service._format_bug_analysis_description(
            message_dict,
            code_analysis,
            None
        )
        
        return {
            "message_id": message_id,
            "is_bug": True,
            "detection": detection,
            "code_analysis": code_analysis,
            "jira_preview": jira_preview
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/integrations/jira/create")
async def create_jira_ticket(
    message_id: int,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    issue_type: Optional[str] = None,
    priority: Optional[str] = None,
    assignee: Optional[str] = None,
    labels: Optional[List[str]] = None,
    research_summary: Optional[str] = None,
    ticket_type: Optional[str] = None
):
    """
    Create a Jira ticket from a Slack message.
    
    Args:
        message_id: Database ID of the Slack message
        summary: Ticket summary (optional, defaults to message text)
        description: Ticket description (optional)
        issue_type: Jira issue type (Bug, Task, Story, Epic)
        priority: Jira priority (Highest, High, Medium, Low)
        assignee: Email of assignee (optional)
        labels: List of labels (optional)
        research_summary: Exa research summary (optional)
        ticket_type: Detected ticket type (optional)
        
    Returns:
        Jira ticket details and Notion update status
    """
    try:
        # Get message from database
        message = cache_service.get_message_by_id(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Convert to dict for jira_service
        message_dict = {
            "text": message.text,
            "channel_name": message.channel_name,
            "user_name": message.user_name,
            "priority_score": message.priority_score,
            "message_id": message.message_id,
            "channel_id": message.channel_id
        }
        
        # Auto-run bug analysis when creating Bug tickets
        code_analysis = None
        if issue_type == "Bug" or ticket_type in ['bug', 'technical_error']:
            try:
                code_analysis = await bug_analyzer.analyze(message_dict)
                logger.info(f"🐛 Bug analysis completed for message {message_id}")
            except Exception as e:
                logger.warning(f"Bug analysis failed (continuing without): {e}")
        
        # Auto-run Exa research for non-bug tickets (if not already provided)
        logger.info(f"🔬 Checking Exa research: code_analysis={code_analysis is not None}, research_summary={research_summary is not None}")
        if not code_analysis and not research_summary:
            try:
                logger.info(f"🔬 Running detect_ticket_type...")
                detection = await exa_service.detect_ticket_type(message_dict)
                logger.info(f"🔬 Detection result: needs_research={detection.get('needs_research')}, type={detection.get('ticket_type')}")
                if detection.get('needs_research'):
                    logger.info(f"🔍 Auto-running Exa research for {detection.get('ticket_type')}")
                    research_result = await exa_service.research_for_ticket(message_dict)
                    research_summary = research_result.get('research_summary')
                    logger.info(f"🔬 Research complete: {len(research_summary) if research_summary else 0} chars")
                    ticket_type = ticket_type or detection.get('ticket_type')
                else:
                    logger.info(f"🔬 Skipping research: needs_research=False")
            except Exception as e:
                logger.warning(f"Exa research failed (continuing without): {e}")
                import traceback
                logger.warning(f"Traceback: {traceback.format_exc()}")
        
        # Create Jira ticket (with bug analysis or research if available)
        jira_result = await jira_service.create_ticket(
            message=message_dict,
            summary=summary,
            description=description,
            issue_type=issue_type,
            priority=priority,
            assignee=assignee,
            labels=labels,
            research_summary=research_summary,
            ticket_type=ticket_type,
            code_analysis=code_analysis
        )
        
        if not jira_result.get('success'):
            raise HTTPException(
                status_code=500, 
                detail=jira_result.get('error', 'Failed to create Jira ticket')
            )
        
        # Update Notion task with Jira link (if Notion is enabled)
        notion_updated = False
        if settings.NOTION_SYNC_ENABLED and settings.NOTION_API_KEY:
            notion_service = NotionSyncService(
                api_key=settings.NOTION_API_KEY,
                database_id=settings.NOTION_DATABASE_ID
            )
            
            # Find Notion page for this message (use client directly)
            notion_page_id = await notion_service.client.find_task_by_slack_message(
                message.message_id,
                message.channel_id
            )
            
            if notion_page_id:
                notion_updated = await notion_service.client.update_task_with_jira_link(
                    notion_page_id,
                    jira_result.get('jira_url'),
                    jira_result.get('jira_key')
                )
        
        return {
            "success": True,
            "jira_key": jira_result.get('jira_key'),
            "jira_url": jira_result.get('jira_url'),
            "notion_updated": notion_updated
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preferences")
async def get_preferences(user_id: str = "default"):
    """
    Get user preferences for priority scoring.
    
    Args:
        user_id: Slack user ID (defaults to "default" for single-user mode)
        
    Returns:
        User preferences dict
    """
    try:
        prefs = cache_service.get_user_preferences(user_id)
        return prefs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preferences")
async def save_preferences(
    user_id: str = Form("default"),
    key_people: Optional[str] = Form(None),
    key_channels: Optional[str] = Form(None),
    key_keywords: Optional[str] = Form(None),
    mute_channels: Optional[str] = Form(None)
):
    """
    Save user preferences for priority scoring.
    
    Args:
        user_id: Slack user ID
        key_people: Comma-separated list of VIP user IDs/names
        key_channels: Comma-separated list of priority channel IDs/names
        key_keywords: Comma-separated list of keywords to boost
        mute_channels: Comma-separated list of channels to de-prioritize
        
    Returns:
        Updated preferences
    """
    try:
        prefs = {
            "key_people": [p.strip() for p in (key_people or "").split(",") if p.strip()],
            "key_channels": [c.strip() for c in (key_channels or "").split(",") if c.strip()],
            "key_keywords": [k.strip() for k in (key_keywords or "").split(",") if k.strip()],
            "mute_channels": [m.strip() for m in (mute_channels or "").split(",") if m.strip()]
        }
        
        result = cache_service.save_user_preferences(user_id, prefs)
        return {"status": "saved", "preferences": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/messages/{message_id}/archive")
async def archive_message(message_id: int):
    """
    Archive a message (mark as done).
    Persists across sessions.
    """
    try:
        result = cache_service.archive_message(message_id)
        if result:
            return {"status": "archived", "message_id": message_id}
        else:
            raise HTTPException(status_code=404, detail="Message not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/integrations/notion/create")
async def create_notion_task(message_id: int):
    """
    Create a Notion task from a Slack message.
    """
    if not settings.NOTION_SYNC_ENABLED or not settings.NOTION_API_KEY:
        raise HTTPException(status_code=400, detail="Notion not configured. Set NOTION_API_KEY and NOTION_SYNC_ENABLED=true")
    
    try:
        # Get message from database
        message = cache_service.get_message_by_id(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Convert to dict
        message_dict = {
            "text": message.text,
            "channel_name": message.channel_name,
            "user_name": message.user_name,
            "priority_score": message.priority_score,
            "message_id": message.message_id,
            "timestamp": str(message.timestamp)
        }
        
        # Initialize Notion service
        notion_service = NotionSyncService(
            api_key=settings.NOTION_API_KEY,
            database_id=settings.NOTION_DATABASE_ID
        )
        
        # Extract task from message
        from ..integrations.notion_service import NotionTaskExtractor
        task = NotionTaskExtractor.extract_task_from_message(message_dict)
        
        if not task:
            raise HTTPException(status_code=400, detail="Could not extract task from message (priority too low?)")
        
        # Create in Notion
        task_id = await notion_service.client.create_task(task)
        
        if task_id:
            return {
                "status": "created",
                "notion_task_id": task_id,
                "notion_url": f"https://notion.so/{task_id.replace('-', '')}"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create Notion task")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

