"""
Sync service - orchestrates message fetching and prioritization.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import time

from ..config import settings
from ..ingestion.slack_ingester import SlackIngester
from ..ai.prioritizer import MessagePrioritizer
from ..database.cache_service import CacheService
from ..integrations.notion_service import NotionSyncService
from .action_item_service import ActionItemService
from .alert_service import AlertService

logger = logging.getLogger(__name__)


class SyncService:
    """Orchestrates message sync and prioritization"""
    
    def __init__(self):
        self.ingester = SlackIngester()
        self.prioritizer = MessagePrioritizer()
        self.cache = CacheService()
        self.notion = NotionSyncService(
            api_key=settings.NOTION_API_KEY,
            database_id=settings.NOTION_DATABASE_ID
        )
        self.action_item_service = ActionItemService()
        self.alert_service = AlertService()
    
    async def sync(
        self,
        channel_ids: Optional[List[str]] = None,
        hours_ago: int = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Full sync: fetch messages and prioritize them.
        
        Args:
            channel_ids: Specific channels to sync (None = all)
            hours_ago: How far back to fetch (None = use config)
            force: Re-process cached messages
            
        Returns:
            Dict with sync results
        """
        start_time = time.time()
        hours_ago = hours_ago or settings.DEFAULT_HOURS_LOOKBACK
        
        logger.info("🚀 Starting full sync...")
        logger.info(f"   Channels: {channel_ids or 'All'}")
        logger.info(f"   Lookback: {hours_ago} hours")
        
        try:
            # Step 1: Fetch messages from Slack
            logger.info("📥 Step 1: Fetching messages from Slack...")
            fetch_result = await self.ingester.sync_channels(
                channel_ids=channel_ids,
                hours_ago=hours_ago
            )
            
            fetch_stats = fetch_result['stats']
            
            # Step 2: Prioritize new messages with AI
            logger.info("🤖 Step 2: AI prioritization...")
            priority_result = await self.prioritizer.prioritize_new_messages()
            
            # Step 2.5: Send instant alerts for critical messages (90+)
            alerts_result = {"status": "disabled", "alerts_sent": 0}
            if priority_result['prioritized'] > 0:
                logger.info("🚨 Step 2.5: Checking for critical alerts...")
                # Get all newly prioritized messages
                recent_messages = self.cache.get_messages_by_score_range(
                    min_score=0,
                    hours_ago=hours_ago,
                    limit=500
                )
                alerts_result = await self.alert_service.send_critical_alerts(recent_messages)
            
            # Step 3: Extract action items and sync to Notion
            notion_result = {"status": "disabled", "tasks_created": 0}
            action_items_result = {"extracted": 0}
            
            if settings.NOTION_SYNC_ENABLED and priority_result['prioritized'] > 0:
                logger.info("📝 Step 3: Processing action items and syncing to Notion...")
                
                # Get high-priority messages that need response (80+)
                high_priority_messages = self.cache.get_messages_by_score_range(
                    min_score=80,  # Changed to 80 for action items
                    hours_ago=hours_ago,
                    limit=100
                )
                
                # Extract action items using LLM
                action_items = await self.action_item_service.process_batch(high_priority_messages)
                action_items_result['extracted'] = len(action_items)
                
                # Sync to Notion (existing service handles this)
                if action_items:
                    notion_result = await self.notion.sync_messages_to_notion(
                        [item['source_message'] for item in action_items]
                    )
                    logger.info(f"✅ Synced {len(action_items)} action items to Notion")
                else:
                    notion_result = {"status": "success", "tasks_created": 0}
                    logger.info("   No action items to sync")
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log sync operation
            status = "success"
            error_message = None
            
            if fetch_stats['errors']:
                status = "partial"
                error_message = f"{len(fetch_stats['errors'])} channel errors"
            
            if priority_result['errors']:
                status = "partial"
                error_message = (error_message or "") + f" {len(priority_result['errors'])} priority errors"
            
            self.cache.log_sync(
                sync_type="manual",
                channels_synced=channel_ids or [],
                hours_lookback=hours_ago,
                messages_fetched=fetch_stats['messages_fetched'],
                new_messages=fetch_stats['new_messages'],
                messages_prioritized=priority_result['prioritized'],
                duration_seconds=duration,
                status=status,
                errors=fetch_stats['errors'] + priority_result['errors'],
                error_message=error_message
            )
            
            logger.info(f"✅ Sync complete in {duration:.1f}s")
            
            return {
                "status": status,
                "duration_seconds": duration,
                "fetch": {
                    "channels_synced": fetch_stats['channels_synced'],
                    "messages_fetched": fetch_stats['messages_fetched'],
                    "new_messages": fetch_stats['new_messages'],
                    "skipped_cached": fetch_stats['skipped_cached'],
                    "errors": fetch_stats['errors']
                },
                "prioritization": {
                    "total_messages": priority_result['total_messages'],
                    "prioritized": priority_result['prioritized'],
                    "errors": priority_result['errors']
                },
                "alerts": alerts_result,
                "action_items": action_items_result,
                "notion": notion_result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Sync failed: {e}")
            
            import traceback
            logger.error(traceback.format_exc())
            
            # Log failed sync
            self.cache.log_sync(
                sync_type="manual",
                channels_synced=channel_ids or [],
                hours_lookback=hours_ago,
                messages_fetched=0,
                new_messages=0,
                messages_prioritized=0,
                duration_seconds=duration,
                status="failed",
                error_message=str(e)
            )
            
            raise
    
    async def quick_sync(self) -> Dict[str, Any]:
        """
        Quick sync - last 2 hours only.
        For frequent background jobs.
        
        Returns:
            Dict with sync results
        """
        logger.info("⚡ Quick sync (2 hours)")
        return await self.sync(hours_ago=2)

