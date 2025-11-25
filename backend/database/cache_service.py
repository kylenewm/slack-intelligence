"""
Cache service for Slack messages and insights.
Handles CRUD operations and deduplication.
"""

import logging
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from .models import SlackMessage, MessageInsight, SyncLog, UserPreference
from .db import SessionLocal

logger = logging.getLogger(__name__)


class CacheService:
    """Handles caching and retrieval of Slack messages"""
    
    @staticmethod
    def message_exists(message_id: str, channel_id: str) -> bool:
        """
        Check if a message already exists in database.
        
        Args:
            message_id: Slack message timestamp
            channel_id: Slack channel ID
            
        Returns:
            True if message exists
        """
        db = SessionLocal()
        try:
            exists = db.query(SlackMessage).filter(
                SlackMessage.message_id == message_id,
                SlackMessage.channel_id == channel_id
            ).first() is not None
            
            return exists
        finally:
            db.close()
    
    @staticmethod
    def save_message(message_data: Dict[str, Any]) -> int:
        """
        Save a Slack message to database.
        
        Args:
            message_data: Dictionary with message fields
            
        Returns:
            Message ID (database primary key)
        """
        db = SessionLocal()
        try:
            # Check if already exists
            existing = db.query(SlackMessage).filter(
                SlackMessage.message_id == message_data['message_id'],
                SlackMessage.channel_id == message_data['channel_id']
            ).first()
            
            if existing:
                logger.debug(f"Message {message_data['message_id']} already exists")
                return existing.id
            
            # Create new message
            message = SlackMessage(**message_data)
            db.add(message)
            db.commit()
            db.refresh(message)
            
            logger.debug(f"💾 Saved message {message.message_id}")
            return message.id
            
        except Exception as e:
            logger.error(f"❌ Error saving message: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    @staticmethod
    def save_batch_messages(messages: List[Dict[str, Any]]) -> int:
        """
        Save multiple messages in a batch.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Number of messages saved
        """
        db = SessionLocal()
        try:
            saved_count = 0
            
            for msg_data in messages:
                # Check if exists
                exists = db.query(SlackMessage).filter(
                    SlackMessage.message_id == msg_data['message_id'],
                    SlackMessage.channel_id == msg_data['channel_id']
                ).first()
                
                if not exists:
                    message = SlackMessage(**msg_data)
                    db.add(message)
                    saved_count += 1
            
            db.commit()
            logger.info(f"💾 Saved {saved_count} new messages")
            return saved_count
            
        except Exception as e:
            logger.error(f"❌ Error saving batch: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    @staticmethod
    def save_insight(
        message_id: int,
        priority_score: int,
        priority_reason: str,
        category: str,
        model_name: str = "gpt-4o-mini",
        action_items: List[str] = None,
        summary: str = None
    ) -> int:
        """
        Save AI insight for a message.
        Also updates the message record with denormalized fields.
        
        Args:
            message_id: Database ID of the message
            priority_score: AI score (0-100)
            priority_reason: Explanation
            category: Message category
            model_name: AI model used
            action_items: Extracted action items
            summary: Summary for long threads
            
        Returns:
            Insight ID
        """
        db = SessionLocal()
        try:
            # Create insight
            insight = MessageInsight(
                message_id=message_id,
                priority_score=priority_score,
                priority_reason=priority_reason,
                category=category,
                model_name=model_name,
                action_items=action_items or [],
                summary=summary
            )
            db.add(insight)
            
            # Update message with denormalized fields
            message = db.query(SlackMessage).filter(SlackMessage.id == message_id).first()
            if message:
                message.priority_score = priority_score
                message.priority_reason = priority_reason
                message.category = category
                message.processed_at = datetime.utcnow()
            
            db.commit()
            db.refresh(insight)
            
            logger.debug(f"💡 Saved insight for message {message_id}: score={priority_score}")
            return insight.id
            
        except Exception as e:
            logger.error(f"❌ Error saving insight: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    @staticmethod
    def get_unprocessed_messages(limit: int = 100) -> List[SlackMessage]:
        """
        Get messages that haven't been prioritized yet.
        
        Args:
            limit: Maximum messages to return
            
        Returns:
            List of SlackMessage objects
        """
        db = SessionLocal()
        try:
            messages = db.query(SlackMessage).filter(
                SlackMessage.processed_at.is_(None)
            ).order_by(
                SlackMessage.timestamp.desc()
            ).limit(limit).all()
            
            return messages
        finally:
            db.close()
    
    @staticmethod
    def get_message_by_id(message_id: int) -> Optional[SlackMessage]:
        """
        Get a single message by its database ID.
        
        Args:
            message_id: Database primary key ID
            
        Returns:
            SlackMessage object or None if not found
        """
        db = SessionLocal()
        try:
            message = db.query(SlackMessage).filter(
                SlackMessage.id == message_id
            ).first()
            
            return message
        finally:
            db.close()
    
    @staticmethod
    def get_messages_by_category(
        category: str,
        hours_ago: int = 24,
        limit: int = 50,
        include_archived: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get messages by priority category.
        
        Args:
            category: "needs_response", "high_priority", "fyi", "low_priority"
            hours_ago: Time window
            limit: Max messages to return
            include_archived: Include archived messages
            
        Returns:
            List of message dictionaries
        """
        db = SessionLocal()
        try:
            since = datetime.utcnow() - timedelta(hours=hours_ago)
            
            query = db.query(SlackMessage).filter(
                SlackMessage.category == category,
                SlackMessage.timestamp >= since
            )
            
            if not include_archived:
                query = query.filter(SlackMessage.archived == False)
            
            messages = query.order_by(
                SlackMessage.priority_score.desc(),
                SlackMessage.timestamp.desc()
            ).limit(limit).all()
            
            # Convert to dicts
            return [CacheService._message_to_dict(msg) for msg in messages]
            
        finally:
            db.close()
    
    @staticmethod
    def get_messages_by_score_range(
        min_score: int,
        max_score: int = 100,
        hours_ago: int = 24,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get messages within a score range"""
        db = SessionLocal()
        try:
            since = datetime.utcnow() - timedelta(hours=hours_ago)
            
            messages = db.query(SlackMessage).filter(
                SlackMessage.priority_score >= min_score,
                SlackMessage.priority_score <= max_score,
                SlackMessage.timestamp >= since,
                SlackMessage.archived == False
            ).order_by(
                SlackMessage.priority_score.desc(),
                SlackMessage.timestamp.desc()
            ).limit(limit).all()
            
            return [CacheService._message_to_dict(msg) for msg in messages]
            
        finally:
            db.close()
    
    @staticmethod
    def log_sync(
        sync_type: str,
        channels_synced: List[str],
        hours_lookback: int,
        messages_fetched: int,
        new_messages: int,
        messages_prioritized: int,
        duration_seconds: float,
        status: str,
        errors: List[Dict] = None,
        error_message: str = None
    ) -> int:
        """
        Log a sync operation.
        
        Returns:
            Sync log ID
        """
        db = SessionLocal()
        try:
            sync_log = SyncLog(
                sync_type=sync_type,
                channels_synced=channels_synced,
                hours_lookback=hours_lookback,
                messages_fetched=messages_fetched,
                new_messages=new_messages,
                messages_prioritized=messages_prioritized,
                duration_seconds=duration_seconds,
                status=status,
                errors=errors or [],
                error_message=error_message,
                started_at=datetime.utcnow() - timedelta(seconds=duration_seconds),
                completed_at=datetime.utcnow()
            )
            
            db.add(sync_log)
            db.commit()
            db.refresh(sync_log)
            
            logger.info(f"📊 Logged sync: {new_messages} new messages, status={status}")
            return sync_log.id
            
        except Exception as e:
            logger.error(f"❌ Error logging sync: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    @staticmethod
    def _message_to_dict(message: SlackMessage) -> Dict[str, Any]:
        """Convert SlackMessage object to dictionary"""
        return {
            "id": message.id,
            "message_id": message.message_id,
            "channel_id": message.channel_id,
            "channel_name": message.channel_name,
            "user_id": message.user_id,
            "user_name": message.user_name,
            "text": message.text,
            "timestamp": message.timestamp.isoformat() if message.timestamp else None,
            "priority_score": message.priority_score,
            "priority_reason": message.priority_reason,
            "category": message.category,
            "thread_ts": message.thread_ts,
            "is_thread_parent": message.is_thread_parent,
            "reply_count": message.reply_count,
            "reactions": message.reactions,
            "has_files": message.has_files,
            "archived": message.archived,
            "read": message.read,
            "link": f"https://slack.com/app_redirect?channel={message.channel_id}&message_ts={message.message_id}"
        }

    @staticmethod
    def get_user_preferences(user_id: str = "default") -> Dict[str, Any]:
        """
        Get user preferences from database.
        
        Args:
            user_id: Slack user ID or "default"
            
        Returns:
            Preferences dict with key_people, key_channels, key_keywords, mute_channels
        """
        db = SessionLocal()
        try:
            pref = db.query(UserPreference).filter(
                UserPreference.slack_user_id == user_id
            ).first()
            
            if pref:
                return {
                    "key_people": pref.key_people or [],
                    "key_channels": pref.key_channels or [],
                    "key_keywords": pref.key_keywords or [],
                    "mute_channels": pref.mute_channels or []
                }
            else:
                # Return empty defaults
                return {
                    "key_people": [],
                    "key_channels": [],
                    "key_keywords": [],
                    "mute_channels": []
                }
        finally:
            db.close()

    @staticmethod
    def save_user_preferences(user_id: str, prefs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save user preferences to database (upsert).
        
        Args:
            user_id: Slack user ID or "default"
            prefs: Dict with key_people, key_channels, key_keywords, mute_channels
            
        Returns:
            Saved preferences
        """
        db = SessionLocal()
        try:
            existing = db.query(UserPreference).filter(
                UserPreference.slack_user_id == user_id
            ).first()
            
            if existing:
                # Update existing
                existing.key_people = prefs.get("key_people", [])
                existing.key_channels = prefs.get("key_channels", [])
                existing.key_keywords = prefs.get("key_keywords", [])
                existing.mute_channels = prefs.get("mute_channels", [])
                existing.updated_at = datetime.utcnow()
            else:
                # Create new
                existing = UserPreference(
                    slack_user_id=user_id,
                    key_people=prefs.get("key_people", []),
                    key_channels=prefs.get("key_channels", []),
                    key_keywords=prefs.get("key_keywords", []),
                    mute_channels=prefs.get("mute_channels", [])
                )
                db.add(existing)
            
            db.commit()
            logger.info(f"✅ Saved preferences for user {user_id}")
            
            return {
                "key_people": existing.key_people or [],
                "key_channels": existing.key_channels or [],
                "key_keywords": existing.key_keywords or [],
                "mute_channels": existing.mute_channels or []
            }
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to save preferences: {e}")
            raise
        finally:
            db.close()

