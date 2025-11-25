"""
Slack message ingestion module.
Fetches messages from Slack API and stores in database.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from ..config import settings
from ..database.cache_service import CacheService
from .message_parser import MessageParser

logger = logging.getLogger(__name__)


class SlackIngester:
    """Fetches messages from Slack workspace"""
    
    def __init__(self):
        """Initialize Slack clients and services"""
        self.bot_client = WebClient(token=settings.SLACK_BOT_TOKEN)
        self.user_client = WebClient(token=settings.SLACK_USER_TOKEN)
        self.cache = CacheService()
        self.parser = MessageParser(self.bot_client)
    
    async def sync_channels(
        self,
        channel_ids: Optional[List[str]] = None,
        hours_ago: int = None
    ) -> Dict[str, Any]:
        """
        Sync messages from specified channels.
        
        Args:
            channel_ids: List of channel IDs (None = all joined channels)
            hours_ago: How far back to fetch (None = use config default)
            
        Returns:
            Dict with sync stats
        """
        hours_ago = hours_ago or settings.DEFAULT_HOURS_LOOKBACK
        
        logger.info(f"🔄 Starting Slack sync (past {hours_ago}h)...")
        
        # Get channel list if not specified
        if not channel_ids:
            channel_ids = await self._get_joined_channels()
        
        # Calculate time threshold
        oldest_ts = (datetime.now() - timedelta(hours=hours_ago)).timestamp()
        
        all_messages = []
        stats = {
            "channels_synced": 0,
            "messages_fetched": 0,
            "new_messages": 0,
            "skipped_cached": 0,
            "errors": []
        }
        
        # Fetch from each channel
        for channel_id in channel_ids:
            try:
                logger.info(f"   📥 Fetching from {channel_id}...")
                
                messages = await self._fetch_channel_messages(
                    channel_id,
                    oldest_ts
                )
                
                # Check cache and filter new messages
                new_messages = []
                for msg in messages:
                    if not self.cache.message_exists(msg['message_id'], msg['channel_id']):
                        new_messages.append(msg)
                    else:
                        stats["skipped_cached"] += 1
                
                all_messages.extend(new_messages)
                stats["channels_synced"] += 1
                stats["messages_fetched"] += len(messages)
                stats["new_messages"] += len(new_messages)
                
                if new_messages:
                    logger.info(f"   ✅ {channel_id}: {len(new_messages)} new messages")
                else:
                    logger.info(f"   ℹ️  {channel_id}: No new messages")
                
            except SlackApiError as e:
                logger.error(f"   ❌ Error fetching {channel_id}: {e}")
                stats["errors"].append({
                    "channel": channel_id,
                    "error": str(e)
                })
        
        # Save new messages to database
        if all_messages:
            saved_count = self.cache.save_batch_messages(all_messages)
            logger.info(f"💾 Saved {saved_count} messages to database")
        
        logger.info(f"✅ Sync complete: {stats['new_messages']} new messages from {stats['channels_synced']} channels")
        return {
            "messages": all_messages,
            "stats": stats
        }
    
    async def _fetch_channel_messages(
        self,
        channel_id: str,
        oldest_ts: float
    ) -> List[Dict[str, Any]]:
        """
        Fetch messages from a single channel.
        
        Args:
            channel_id: Slack channel ID
            oldest_ts: Unix timestamp for oldest message
            
        Returns:
            List of parsed message dictionaries
        """
        messages = []
        cursor = None
        page_count = 0
        max_pages = 10  # Safety limit
        
        while page_count < max_pages:
            try:
                result = self.bot_client.conversations_history(
                    channel=channel_id,
                    oldest=str(oldest_ts),
                    limit=200,  # Max per page
                    cursor=cursor
                )
                
                batch = result.get('messages', [])
                messages.extend(batch)
                page_count += 1
                
                logger.debug(f"      Fetched page {page_count}: {len(batch)} messages")
                
                # Check if more pages
                if not result.get('has_more'):
                    break
                    
                cursor = result.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break
                    
            except SlackApiError as e:
                # Handle rate limiting
                if e.response.status_code == 429:
                    retry_after = int(e.response.headers.get('Retry-After', 60))
                    logger.warning(f"⚠️  Rate limited on {channel_id}. Waiting {retry_after}s...")
                    await asyncio.sleep(retry_after)
                    continue
                logger.error(f"❌ Slack API error on page {page_count}: {e}")
                break
        
        # Parse and enrich messages
        parsed_messages = []
        for msg in messages:
            parsed = await self.parser.parse_message(msg, channel_id)
            if parsed:
                parsed_messages.append(parsed)
        
        return parsed_messages
    
    async def _get_joined_channels(self) -> List[str]:
        """
        Get list of channels the bot has joined.
        
        Returns:
            List of channel IDs
        """
        try:
            result = self.bot_client.conversations_list(
                types="public_channel,private_channel",
                exclude_archived=True,
                limit=1000
            )
            
            channels = [
                ch['id'] for ch in result['channels']
                if ch.get('is_member', False)
            ]
            
            logger.info(f"📋 Found {len(channels)} joined channels")
            return channels
            
        except SlackApiError as e:
            logger.error(f"❌ Error getting channels: {e}")
            return []
    
    async def fetch_dms(self, hours_ago: int = None) -> List[Dict[str, Any]]:
        """
        Fetch direct messages.
        
        Args:
            hours_ago: How far back to fetch
            
        Returns:
            List of DM messages
        """
        hours_ago = hours_ago or settings.DEFAULT_HOURS_LOOKBACK
        oldest_ts = (datetime.now() - timedelta(hours=hours_ago)).timestamp()
        
        logger.info(f"📬 Fetching DMs from past {hours_ago}h...")
        
        try:
            # Get list of DM conversations
            result = self.bot_client.conversations_list(
                types="im",  # Direct messages
                limit=1000
            )
            
            dm_channels = [ch['id'] for ch in result.get('channels', [])]
            logger.info(f"   Found {len(dm_channels)} DM conversations")
            
            # Fetch messages from each DM
            all_dms = []
            for dm_channel in dm_channels:
                messages = await self._fetch_channel_messages(dm_channel, oldest_ts)
                all_dms.extend(messages)
            
            logger.info(f"✅ Fetched {len(all_dms)} DM messages")
            return all_dms
            
        except SlackApiError as e:
            logger.error(f"❌ Error fetching DMs: {e}")
            return []
    
    async def fetch_mentions(
        self,
        user_id: str = None,
        hours_ago: int = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch messages that mention a specific user using search API.
        
        Args:
            user_id: Slack user ID (None = use bot's user ID)
            hours_ago: How far back to search
            
        Returns:
            List of messages mentioning the user
        """
        hours_ago = hours_ago or settings.DEFAULT_HOURS_LOOKBACK
        
        # Get bot's user ID if not specified
        if not user_id:
            try:
                auth_result = self.bot_client.auth_test()
                user_id = auth_result['user_id']
            except SlackApiError as e:
                logger.error(f"❌ Error getting bot user ID: {e}")
                return []
        
        logger.info(f"📌 Fetching mentions of <@{user_id}> from past {hours_ago}h...")
        
        try:
            # Calculate date range for search
            oldest_date = datetime.now() - timedelta(hours=hours_ago)
            query = f"<@{user_id}> after:{oldest_date.strftime('%Y-%m-%d')}"
            
            # Use user token for search (bot token doesn't have search permission)
            result = self.user_client.search_messages(
                query=query,
                count=100,
                sort='timestamp',
                sort_dir='desc'
            )
            
            mentions = []
            for match in result.get('messages', {}).get('matches', []):
                parsed = await self.parser.parse_message(
                    match,
                    match.get('channel', {}).get('id', 'unknown')
                )
                if parsed:
                    mentions.append(parsed)
            
            logger.info(f"✅ Found {len(mentions)} mentions")
            return mentions
            
        except SlackApiError as e:
            logger.error(f"❌ Error fetching mentions: {e}")
            logger.error(f"   Make sure SLACK_USER_TOKEN has search:read scope")
            return []
    
    async def fetch_thread_replies(
        self,
        channel_id: str,
        thread_ts: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch all replies in a thread.
        
        Args:
            channel_id: Channel containing the thread
            thread_ts: Thread parent timestamp
            
        Returns:
            List of reply messages
        """
        try:
            result = self.bot_client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=1000
            )
            
            messages = result.get('messages', [])
            
            # Parse replies (skip first message which is the parent)
            replies = []
            for msg in messages[1:]:  # Skip parent
                parsed = await self.parser.parse_message(msg, channel_id)
                if parsed:
                    replies.append(parsed)
            
            logger.info(f"📎 Fetched {len(replies)} replies from thread {thread_ts}")
            return replies
            
        except SlackApiError as e:
            logger.error(f"❌ Error fetching thread replies: {e}")
            return []

