"""
Message parser for Slack API responses.
Converts raw Slack JSON into our database format.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)


class MessageParser:
    """Parses Slack API responses into structured message data"""
    
    def __init__(self, slack_client: WebClient):
        """
        Initialize parser.
        
        Args:
            slack_client: Slack WebClient for enriching data
        """
        self.client = slack_client
        self._user_cache = {}  # Cache user info
        self._channel_cache = {}  # Cache channel info
    
    async def parse_message(
        self,
        raw_message: Dict[str, Any],
        channel_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Parse raw Slack message into our format.
        Filters out bots, system messages, etc.
        
        Args:
            raw_message: Raw message from Slack API
            channel_id: Channel ID
            
        Returns:
            Parsed message dict or None if should be filtered
        """
        # Skip bot messages and system messages
        if self._should_skip_message(raw_message):
            return None
        
        # Extract basic fields
        message_id = raw_message.get('ts', '')
        user_id = raw_message.get('user', 'unknown')
        text = raw_message.get('text', '')
        
        # Get user name
        user_name = await self._get_user_name(user_id)
        
        # Get channel name
        channel_name = await self._get_channel_name(channel_id)
        
        # Parse timestamp - ALWAYS use UTC
        try:
            timestamp = datetime.utcfromtimestamp(float(message_id))
        except (ValueError, TypeError):
            timestamp = datetime.utcnow()
        
        # Extract thread info
        thread_ts = raw_message.get('thread_ts')
        is_thread_parent = thread_ts == message_id if thread_ts else False
        reply_count = raw_message.get('reply_count', 0)
        
        # Extract reactions
        reactions = raw_message.get('reactions', [])
        has_reactions = len(reactions) > 0
        reaction_count = sum(r.get('count', 0) for r in reactions)
        
        # Extract mentioned users
        mentioned_users = self._extract_mentions(text)
        
        # Extract files
        files = raw_message.get('files', [])
        has_files = len(files) > 0
        
        # Build parsed message
        parsed = {
            "message_id": message_id,
            "channel_id": channel_id,
            "channel_name": channel_name,
            "user_id": user_id,
            "user_name": user_name,
            "text": text,
            "timestamp": timestamp,
            "thread_ts": thread_ts,
            "is_thread_parent": is_thread_parent,
            "reply_count": reply_count,
            "has_reactions": has_reactions,
            "reaction_count": reaction_count,
            "reactions": reactions,
            "mentioned_users": mentioned_users,
            "has_files": has_files,
            "files": [self._parse_file(f) for f in files],
            "raw_data": raw_message,
            "fetched_at": datetime.now(timezone.utc)
        }
        
        return parsed
    
    def _should_skip_message(self, raw_message: Dict[str, Any]) -> bool:
        """
        Determine if message should be skipped.
        
        Args:
            raw_message: Raw Slack message
            
        Returns:
            True if should skip
        """
        # Skip system messages
        skip_subtypes = [
            # 'bot_message',  # DISABLED FOR TESTING - Allow bot messages
            'channel_join',
            'channel_leave',
            'channel_archive',
            'channel_unarchive',
            'channel_name',
            'channel_purpose',
            'channel_topic',
            'pinned_item',
            'unpinned_item'
        ]
        
        if raw_message.get('subtype') in skip_subtypes:
            return True
        
        # Skip bot messages (even without subtype)
        # Allow specific test/simulation bots, but filter out automated spam
        
        # Simulation bots for demo (User IDs, not bot_ids since they're user-bots)
        allowed_simulation_users = [
            'U09N761B1RD',  # Manager Bot
            'U09NG7YLB2P',  # Metrics Bot
            'U09P1GUPDH7',  # Coworker Bot
        ]
        
        # Check if message is from a bot
        bot_id = raw_message.get('bot_id')
        user_id = raw_message.get('user')
        
        # Allow messages from simulation user-bots
        if user_id in allowed_simulation_users:
            return False  # Don't skip simulation bot messages
        
        # Skip all other bot messages
        if bot_id:
            return True
        
        # Skip messages without text
        if not raw_message.get('text', '').strip():
            return True
        
        return False
    
    async def _get_user_name(self, user_id: str) -> str:
        """
        Get user's display name from Slack API.
        Uses cache to minimize API calls.
        
        Args:
            user_id: Slack user ID
            
        Returns:
            User's display name or user ID if lookup fails
        """
        if user_id in self._user_cache:
            return self._user_cache[user_id]
        
        try:
            result = self.client.users_info(user=user_id)
            user = result['user']
            
            # Prefer display name, fall back to real name
            name = (
                user.get('profile', {}).get('display_name') or
                user.get('profile', {}).get('real_name') or
                user.get('name') or
                user_id
            )
            
            self._user_cache[user_id] = name
            return name
            
        except SlackApiError as e:
            logger.warning(f"⚠️  Could not fetch user {user_id}: {e}")
            return user_id
    
    async def _get_channel_name(self, channel_id: str) -> str:
        """
        Get channel name from Slack API.
        Uses cache to minimize API calls.
        
        Args:
            channel_id: Slack channel ID
            
        Returns:
            Channel name or channel ID if lookup fails
        """
        if channel_id in self._channel_cache:
            return self._channel_cache[channel_id]
        
        try:
            result = self.client.conversations_info(channel=channel_id)
            channel = result['channel']
            
            name = channel.get('name') or channel.get('id') or channel_id
            
            self._channel_cache[channel_id] = name
            return name
            
        except SlackApiError as e:
            logger.warning(f"⚠️  Could not fetch channel {channel_id}: {e}")
            return channel_id
    
    def _extract_mentions(self, text: str) -> List[str]:
        """
        Extract user mentions from message text.
        
        Args:
            text: Message text
            
        Returns:
            List of user IDs mentioned
        """
        import re
        
        # Match <@U123456> patterns
        mentions = re.findall(r'<@(U[A-Z0-9]+)>', text)
        return list(set(mentions))  # Deduplicate
    
    def _parse_file(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse file attachment data.
        
        Args:
            file_data: Raw file data from Slack
            
        Returns:
            Simplified file dict
        """
        return {
            "id": file_data.get('id'),
            "name": file_data.get('name'),
            "title": file_data.get('title'),
            "mimetype": file_data.get('mimetype'),
            "size": file_data.get('size'),
            "url": file_data.get('url_private'),
            "thumbnail": file_data.get('thumb_360')
        }

