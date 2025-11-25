"""
Action Item Service - Extracts actionable tasks from messages using LLM.
"""

import logging
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI

from ..config import settings

logger = logging.getLogger(__name__)
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


class ActionItemService:
    """Extract and process action items from high-priority messages"""
    
    def __init__(self):
        self.min_score = 80  # Only process high-priority messages
    
    async def extract_action_items(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract action items from a message using LLM.
        
        Args:
            message: Message dict with text, user_name, priority_score, etc.
            
        Returns:
            Dict with action item details or None if no action needed
        """
        priority_score = message.get('priority_score', 0)
        category = message.get('category', '')
        
        # Only process high-priority messages that need response
        if priority_score < self.min_score or category != 'needs_response':
            return None
        
        text = message.get('text', '')
        user_name = message.get('user_name', 'Unknown')
        channel_name = message.get('channel_name', 'Unknown')
        
        logger.info(f"🎯 Extracting action items from message (score: {priority_score})")
        
        # Use LLM to extract action item
        try:
            action_item = await self._extract_with_llm(text, user_name, channel_name, message)
            
            if action_item:
                logger.info(f"✅ Extracted action item: {action_item['title'][:50]}...")
                return {
                    'title': action_item['title'],
                    'description': action_item['description'],
                    'priority': action_item['priority'],
                    'due_date': action_item.get('due_date'),
                    'owner': action_item.get('owner'),
                    'source_message': message
                }
            else:
                logger.info("   No actionable items found")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to extract action items: {e}")
            return None
    
    async def _extract_with_llm(
        self, 
        text: str, 
        user_name: str, 
        channel_name: str,
        message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Use LLM to intelligently extract action items"""
        
        prompt = f"""Analyze this Slack message and extract any actionable tasks.

**Message from {user_name} in #{channel_name}:**
{text}

**Priority Context:**
- Score: {message.get('priority_score', 0)}/100
- Reason: {message.get('priority_reason', 'N/A')}

Extract:
1. A clear, concise action item title (max 100 chars)
2. Any mentioned due date or deadline
3. Who should own this (if mentioned)
4. Priority level (Urgent/High/Medium)

If this message contains NO actionable task (just FYI, discussion, or question), respond with "NO_ACTION".

Format your response as:
TITLE: [concise action item]
DUE: [date if mentioned, or "None"]
OWNER: [person if mentioned, or "Unassigned"]
PRIORITY: [Urgent/High/Medium]
DESCRIPTION: [fuller context and details]
"""
        
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "You extract clear, actionable tasks from Slack messages. Be concise and specific."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )
        
        result = response.choices[0].message.content.strip()
        
        if "NO_ACTION" in result:
            return None
        
        # Parse LLM response
        lines = result.split('\n')
        action_item = {
            'title': '',
            'description': '',
            'due_date': None,
            'owner': None,
            'priority': 'High'
        }
        
        for line in lines:
            line = line.strip()
            if line.startswith('TITLE:'):
                action_item['title'] = line.replace('TITLE:', '').strip()
            elif line.startswith('DUE:'):
                due = line.replace('DUE:', '').strip()
                action_item['due_date'] = None if due.lower() in ['none', 'n/a'] else due
            elif line.startswith('OWNER:'):
                owner = line.replace('OWNER:', '').strip()
                action_item['owner'] = None if owner.lower() in ['unassigned', 'none'] else owner
            elif line.startswith('PRIORITY:'):
                action_item['priority'] = line.replace('PRIORITY:', '').strip()
            elif line.startswith('DESCRIPTION:'):
                action_item['description'] = line.replace('DESCRIPTION:', '').strip()
        
        # Fallback to message text if no title extracted
        if not action_item['title']:
            action_item['title'] = text[:100]
        
        # Add message context to description
        if not action_item['description']:
            action_item['description'] = text
        
        return action_item
    
    async def process_batch(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process multiple messages and extract action items.
        
        Args:
            messages: List of message dicts
            
        Returns:
            List of extracted action items
        """
        action_items = []
        
        for message in messages:
            item = await self.extract_action_items(message)
            if item:
                action_items.append(item)
        
        logger.info(f"📋 Extracted {len(action_items)} action items from {len(messages)} messages")
        return action_items

