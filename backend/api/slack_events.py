"""
Slack Events API Handler.
Receives real-time events from Slack (Push vs Poll).
"""

import logging
import hmac
import hashlib
import time
import json
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Header
from typing import Dict, Any
from slack_sdk.web.async_client import AsyncWebClient

from ..config import settings
from ..services.sync_service import SyncService
from ..integrations.exa_service import ExaSearchService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["slack_events"])

async def verify_slack_signature(request: Request, x_slack_request_timestamp: str, x_slack_signature: str):
    """
    Verify that the request actually came from Slack.
    """
    if not settings.SLACK_SIGNING_SECRET:
        logger.warning("⚠️ SLACK_SIGNING_SECRET not set. Skipping signature verification (INSECURE).")
        return

    # Check if timestamp is too old (replay attack)
    if abs(time.time() - int(x_slack_request_timestamp)) > 60 * 5:
        raise HTTPException(status_code=400, detail="Request timestamp expired")

    # Get raw body
    body = await request.body()
    
    # Create signature
    sig_basestring = f"v0:{x_slack_request_timestamp}:{body.decode('utf-8')}"
    my_signature = "v0=" + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode("utf-8"),
        sig_basestring.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(my_signature, x_slack_signature):
        logger.error(f"Invalid signature. Expected {my_signature}, got {x_slack_signature}")
        raise HTTPException(status_code=400, detail="Invalid Slack signature")

async def process_message_event(event: Dict[str, Any]):
    """
    Process a single message event in the background.
    This runs ingestion -> AI -> Actions for just ONE message.
    """
    try:
        # Extract message details
        channel_id = event.get("channel")
        user_id = event.get("user")
        text = event.get("text")
        ts = event.get("ts")
        
        if not channel_id or not text or not user_id:
            return

        # Ignore bot messages to prevent loops
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            return

        logger.info(f"⚡ Processing real-time message from {user_id} in {channel_id}")
        
        # Trigger the sync service for just this channel/message
        sync_service = SyncService()
        await sync_service.sync(channel_ids=[channel_id], hours_ago=1)
        
    except Exception as e:
        logger.error(f"Error processing event: {e}")

async def process_app_mention(event: Dict[str, Any]):
    """
    Handle @Traverse mentions in Slack.
    Performs RAG + Research and replies in thread.
    """
    try:
        channel_id = event.get("channel")
        user_id = event.get("user")
        text = event.get("text")
        ts = event.get("ts")
        thread_ts = event.get("thread_ts", ts) # Reply in thread if it exists, else start one
        
        logger.info(f"🤖 Processing app mention: {text}")
        
        slack_client = AsyncWebClient(token=settings.SLACK_BOT_TOKEN)
        
        # 1. React to acknowledge
        await slack_client.reactions_add(
            channel=channel_id,
            timestamp=ts,
            name="eyes"
        )
        
        # 2. Run Research (which uses Context Engine + RAG internally)
        exa_service = ExaSearchService()
        
        # Mock message object for the service
        message_obj = {
            "text": text,
            "channel_name": "unknown", # We could fetch this, but it's slow
            "user_name": user_id,
            "priority_score": 100 # Force attention
        }
        
        result = await exa_service.research_for_ticket(message_obj)
        summary = result.get("research_summary")
        
        # 3. Reply
        if summary:
            reply_text = f"🤖 *Research Complete*\n\n{summary}"
        else:
            reply_text = "I analyzed your request but couldn't find relevant external research. However, based on our internal context, this might be related to recent changes in the codebase."
            
        await slack_client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=reply_text,
            unfurl_links=False
        )
        
        # Remove eyes, add check
        await slack_client.reactions_remove(
            channel=channel_id,
            timestamp=ts,
            name="eyes"
        )
        await slack_client.reactions_add(
            channel=channel_id,
            timestamp=ts,
            name="white_check_mark"
        )
        
    except Exception as e:
        logger.error(f"Error processing mention: {e}")
        # Try to error reply
        try:
            slack_client = AsyncWebClient(token=settings.SLACK_BOT_TOKEN)
            await slack_client.chat_postMessage(
                channel=event.get("channel"),
                thread_ts=event.get("ts"),
                text=f"❌ Error processing request: {str(e)}"
            )
        except:
            pass

@router.post("/api/slack/events")
async def slack_events(
    request: Request, 
    background_tasks: BackgroundTasks,
    x_slack_request_timestamp: str = Header(None),
    x_slack_signature: str = Header(None)
):
    """
    Endpoint for Slack Events API.
    """
    # 1. Verify Signature
    if x_slack_request_timestamp and x_slack_signature:
        await verify_slack_signature(request, x_slack_request_timestamp, x_slack_signature)
    
    # 2. Parse Body
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # 3. Handle URL Verification (Handshake)
    if body.get("type") == "url_verification":
        logger.info("✅ Handling Slack URL verification challenge")
        return {"challenge": body.get("challenge")}

    # 4. Handle Event Callback
    if body.get("type") == "event_callback":
        event = body.get("event", {})
        event_type = event.get("type")
        
        if event_type == "message":
            background_tasks.add_task(process_message_event, event)
        
        elif event_type == "app_mention":
            background_tasks.add_task(process_app_mention, event)
            
        return {"status": "ok"}

    return {"status": "ignored"}
