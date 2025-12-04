"""
Inbox service - provides smart inbox views.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone

from ..config import settings
from ..database.cache_service import CacheService

logger = logging.getLogger(__name__)


class InboxService:
    """Smart inbox functionality"""
    
    def __init__(self):
        self.cache = CacheService()
    
    async def get_all(
        self,
        hours_ago: int = 24,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all messages sorted by priority.
        
        Args:
            hours_ago: Time window
            limit: Max messages
            
        Returns:
            List of messages
        """
        messages = self.cache.get_messages_by_score_range(
            min_score=0,
            max_score=100,
            hours_ago=hours_ago,
            limit=limit
        )
        
        logger.info(f"📬 Retrieved {len(messages)} messages (all)")
        return messages
    
    async def get_needs_response(
        self,
        hours_ago: int = 24,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get messages that need your response.
        High urgency messages with direct questions.
        
        Args:
            hours_ago: Time window
            limit: Max messages
            
        Returns:
            List of messages needing response
        """
        messages = self.cache.get_messages_by_category(
            category="needs_response",
            hours_ago=hours_ago,
            limit=limit
        )
        
        logger.info(f"💬 Retrieved {len(messages)} messages needing response")
        return messages
    
    async def get_high_priority(
        self,
        hours_ago: int = 24,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get high priority messages.
        Important but not requiring immediate response.
        
        Args:
            hours_ago: Time window
            limit: Max messages
            
        Returns:
            List of high priority messages
        """
        messages = self.cache.get_messages_by_category(
            category="high_priority",
            hours_ago=hours_ago,
            limit=limit
        )
        
        logger.info(f"🔥 Retrieved {len(messages)} high priority messages")
        return messages
    
    async def get_fyi(
        self,
        hours_ago: int = 24,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get FYI messages.
        Medium priority context messages.
        
        Args:
            hours_ago: Time window
            limit: Max messages
            
        Returns:
            List of FYI messages
        """
        messages = self.cache.get_messages_by_category(
            category="fyi",
            hours_ago=hours_ago,
            limit=limit
        )
        
        logger.info(f"📋 Retrieved {len(messages)} FYI messages")
        return messages
    
    async def get_low_priority(
        self,
        hours_ago: int = 24,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get low priority messages.
        Can be skipped or archived.
        
        Args:
            hours_ago: Time window
            limit: Max messages
            
        Returns:
            List of low priority messages
        """
        messages = self.cache.get_messages_by_category(
            category="low_priority",
            hours_ago=hours_ago,
            limit=limit,
            include_archived=True
        )
        
        logger.info(f"⬇️ Retrieved {len(messages)} low priority messages")
        return messages
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get system statistics.
        
        Returns:
            Dict with stats
        """
        from ..database.db import SessionLocal
        from ..database.models import SlackMessage, SyncLog
        
        db = SessionLocal()
        try:
            # Message counts by category (last 24h)
            # All timestamps should be UTC
            since = datetime.utcnow() - timedelta(hours=24)
            
            total_messages = db.query(SlackMessage).filter(
                SlackMessage.timestamp >= since
            ).count()
            
            needs_response = db.query(SlackMessage).filter(
                SlackMessage.timestamp >= since,
                SlackMessage.category == "needs_response",
                SlackMessage.archived == False
            ).count()
            
            high_priority = db.query(SlackMessage).filter(
                SlackMessage.timestamp >= since,
                SlackMessage.category == "high_priority",
                SlackMessage.archived == False
            ).count()
            
            fyi = db.query(SlackMessage).filter(
                SlackMessage.timestamp >= since,
                SlackMessage.category == "fyi",
                SlackMessage.archived == False
            ).count()
            
            low_priority = db.query(SlackMessage).filter(
                SlackMessage.timestamp >= since,
                SlackMessage.category == "low_priority"
            ).count()
            
            # Latest sync
            latest_sync = db.query(SyncLog).order_by(
                SyncLog.started_at.desc()
            ).first()
            
            sync_info = None
            if latest_sync:
                sync_info = {
                    "last_sync": latest_sync.started_at.isoformat(),
                    "status": latest_sync.status,
                    "messages_fetched": latest_sync.messages_fetched,
                    "new_messages": latest_sync.new_messages
                }
            
            return {
                "time_window": "24 hours",
                "total_messages": total_messages,
                "by_category": {
                    "needs_response": needs_response,
                    "high_priority": high_priority,
                    "fyi": fyi,
                    "low_priority": low_priority
                },
                "latest_sync": sync_info,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        finally:
            db.close()

