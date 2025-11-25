"""
AI-powered message prioritization.
Uses LLM to score messages by importance/urgency.
"""

import logging
import json
from typing import List, Dict, Any
from openai import AsyncOpenAI

from ..config import settings
from ..database.cache_service import CacheService

logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


class MessagePrioritizer:
    """AI-powered message prioritization"""
    
    def __init__(self, user_preferences: Dict[str, Any] = None):
        """
        Initialize prioritizer.
        
        Args:
            user_preferences: Dict with key_people, key_channels, key_keywords
        """
        self.user_preferences = user_preferences or settings.get_user_preferences()
        self.cache = CacheService()
    
    async def prioritize_new_messages(self) -> Dict[str, Any]:
        """
        Prioritize all unprocessed messages in the database.
        
        Returns:
            Dict with prioritization stats
        """
        logger.info("🤖 Starting AI prioritization...")
        
        # Get unprocessed messages
        messages = self.cache.get_unprocessed_messages(
            limit=settings.MAX_MESSAGES_PER_SYNC
        )
        
        if not messages:
            logger.info("   No unprocessed messages found")
            return {
                "total_messages": 0,
                "prioritized": 0,
                "errors": []
            }
        
        logger.info(f"   Found {len(messages)} unprocessed messages")
        
        # Convert to dicts for processing
        message_dicts = [self._message_obj_to_dict(msg) for msg in messages]
        
        # Prioritize in batches
        prioritized = await self.prioritize_batch(message_dicts)
        
        # Save insights to database
        saved_count = 0
        errors = []
        
        for msg in prioritized:
            try:
                self.cache.save_insight(
                    message_id=msg['db_id'],
                    priority_score=msg['priority_score'],
                    priority_reason=msg['priority_reason'],
                    category=msg['category'],
                    model_name=settings.PRIORITIZATION_MODEL
                )
                saved_count += 1
            except Exception as e:
                logger.error(f"❌ Error saving insight for message {msg['db_id']}: {e}")
                errors.append({
                    "message_id": msg['db_id'],
                    "error": str(e)
                })
        
        logger.info(f"✅ Prioritized {saved_count} messages")
        
        return {
            "total_messages": len(messages),
            "prioritized": saved_count,
            "errors": errors
        }
    
    async def prioritize_batch(
        self,
        messages: List[Dict[str, Any]],
        batch_size: int = None
    ) -> List[Dict[str, Any]]:
        """
        Prioritize a batch of messages with AI.
        
        Args:
            messages: List of message dicts
            batch_size: Process this many at once (None = use config)
            
        Returns:
            Messages with priority_score, priority_reason, and category added
        """
        batch_size = batch_size or settings.PRIORITIZATION_BATCH_SIZE
        
        logger.info(f"🤖 Prioritizing {len(messages)} messages in batches of {batch_size}...")
        
        prioritized = []
        
        # Process in batches to avoid token limits
        for i in range(0, len(messages), batch_size):
            batch = messages[i:i+batch_size]
            logger.info(f"   Processing batch {i//batch_size + 1}/{(len(messages)-1)//batch_size + 1}...")
            
            batch_results = await self._prioritize_single_batch(batch)
            prioritized.extend(batch_results)
        
        logger.info(f"✅ Prioritization complete")
        return prioritized
    
    async def _prioritize_single_batch(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Prioritize a single batch with one AI call.
        
        Args:
            messages: List of message dicts
            
        Returns:
            Messages with AI priorities added
        """
        # Format messages for AI
        messages_text = self._format_messages_for_ai(messages)
        
        # Build prompt with user preferences
        prompt = self._build_prioritization_prompt(messages_text, len(messages))
        
        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await openai_client.chat.completions.create(
                    model=settings.PRIORITIZATION_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an AI assistant that helps prioritize Slack messages. Return only valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"},
                    max_tokens=2000,
                    timeout=60.0
                )
                
                # Parse AI response with validation
                content = response.choices[0].message.content
                ai_response = json.loads(content)
                priorities = ai_response.get('priorities', [])
                
                # Validate we got the right number of priorities
                if len(priorities) != len(messages):
                    logger.warning(f"⚠️  AI returned {len(priorities)} priorities for {len(messages)} messages")
                    if attempt < max_retries - 1:
                        logger.info(f"   Retrying attempt {attempt + 2}/{max_retries}...")
                        continue
                
                # Merge priorities back into messages
                return self._merge_priorities(messages, priorities)
                
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️  JSON decode error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"   Retrying attempt {attempt + 2}/{max_retries}...")
                    continue
                else:
                    logger.error("❌ All retry attempts failed, using fallback prioritization")
                    return self._fallback_prioritization(messages)
                    
            except Exception as e:
                logger.error(f"❌ AI prioritization failed on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"   Retrying attempt {attempt + 2}/{max_retries}...")
                    continue
                else:
                    logger.error("❌ All retry attempts failed, using fallback prioritization")
                    return self._fallback_prioritization(messages)
        
        # This should never be reached, but just in case
        return self._fallback_prioritization(messages)
    
    def _fallback_prioritization(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fallback prioritization when AI fails.
        Uses simple keyword matching and @mention detection.
        
        Args:
            messages: List of message dicts
            
        Returns:
            Messages with fallback priorities
        """
        logger.info("🔄 Using fallback prioritization...")
        
        prioritized = []
        for msg in messages:
            text = msg.get('text', '').lower()
            user_name = msg.get('user_name', '')
            channel_name = msg.get('channel_name', '')
            
            # Simple keyword-based scoring
            score = 50  # Default medium priority
            reason = "Fallback prioritization"
            category = "fyi"
            
            # High priority indicators
            if any(word in text for word in ['urgent', 'asap', 'emergency', 'critical', 'blocking']):
                score = 90
                reason = "Contains urgent keywords"
                category = "needs_response"
            elif any(word in text for word in ['@', 'mention']):
                score = 85
                reason = "Contains @mention"
                category = "needs_response"
            elif any(word in text for word in ['production', 'down', 'error', 'issue']):
                score = 80
                reason = "Production-related keywords"
                category = "high_priority"
            elif any(word in text for word in ['decision', 'approval', 'review']):
                score = 75
                reason = "Decision required"
                category = "high_priority"
            elif any(word in text for word in ['fyi', 'update', 'reminder']):
                score = 40
                reason = "Informational"
                category = "fyi"
            elif any(word in text for word in ['lol', 'coffee', 'lunch', 'casual']):
                score = 20
                reason = "Casual conversation"
                category = "low_priority"
            
            prioritized.append({
                **msg,
                "priority_score": score,
                "priority_reason": reason,
                "category": category
            })
        
        logger.info(f"✅ Fallback prioritization complete for {len(messages)} messages")
        return prioritized
    
    def _format_messages_for_ai(
        self,
        messages: List[Dict[str, Any]]
    ) -> str:
        """
        Format messages into text for AI analysis.
        
        Args:
            messages: List of message dicts
            
        Returns:
            Formatted text string
        """
        formatted = []
        
        for i, msg in enumerate(messages, 1):
            channel = msg.get('channel_name', msg.get('channel_id', 'Unknown'))
            user = msg.get('user_name', msg.get('user_id', 'Unknown'))
            text = msg.get('text', '')[:300]  # Truncate long messages
            
            # Add context indicators
            indicators = []
            if msg.get('mentioned_users'):
                indicators.append(f"mentions {len(msg.get('mentioned_users', []))} users")
            if msg.get('is_thread_parent'):
                indicators.append(f"{msg.get('reply_count', 0)} replies")
            if msg.get('has_files'):
                indicators.append("has files")
            if msg.get('reactions'):
                indicators.append(f"{msg.get('reaction_count', 0)} reactions")
            
            context = f" [{', '.join(indicators)}]" if indicators else ""
            
            formatted.append(
                f"{i}. [{channel}] {user}{context}: {text}"
            )
        
        return "\n".join(formatted)
    
    def _build_prioritization_prompt(self, messages_text: str, message_count: int) -> str:
        """
        Build the prioritization prompt with user context.
        
        Args:
            messages_text: Formatted messages
            message_count: Number of messages
            
        Returns:
            Complete prompt string
        """
        # Extract user preferences
        key_people = self.user_preferences.get('key_people', [])
        key_keywords = self.user_preferences.get('key_keywords', [])
        key_channels = self.user_preferences.get('key_channels', [])
        
        prompt = f"""Analyze these {message_count} Slack messages and assign priority scores (0-100) and categories.

PRIORITY SCORING GUIDELINES:

🚨 URGENT (90-100): Requires immediate action
• Direct questions explicitly asking for your input or decision
• Critical blockers mentioned (deployment, production issue, downtime)
• Time-sensitive with explicit deadline (today, EOD, urgent)
• Messages containing: "can you", "need your", "waiting on you", "blocking"
• Emergency or crisis situations

🔥 HIGH PRIORITY (70-89): Important but not immediate
• You're mentioned in important discussions
• Key project updates or decisions being made  
• Questions from stakeholders (but not blocking them)
• Important meetings or action items
• Messages from key people about key topics

📋 MEDIUM (50-69): FYI / Context
• Relevant team discussions you should know about
• Updates on projects you're involved with
• Informational announcements
• General team communication on relevant topics
• Discussions where your context would be useful

⬇️ LOW (0-49): Can skip/archive
• Off-topic casual chatter or social conversations
• Automated notifications and bot messages
• Threads you're not involved in
• Topics outside your scope
• Resolved discussions

CATEGORIES:
- "needs_response": Requires direct action/response from you (score usually 80+)
- "high_priority": Important to read soon (score 70-89)
- "fyi": Useful context, read when available (score 50-69)
- "low_priority": Can skip or archive (score 0-49)

USER CONTEXT (prioritize these):
- Key people: {', '.join(key_people) if key_people else 'Not specified'}
- Key topics/projects: {', '.join(key_keywords) if key_keywords else 'Not specified'}
- Key channels: {', '.join(key_channels) if key_channels else 'Not specified'}

MESSAGES TO ANALYZE:
{messages_text}

Return JSON with this exact format:
{{
  "priorities": [
    {{
      "message_number": 1,
      "score": 95,
      "reason": "Direct question with deadline from key stakeholder",
      "category": "needs_response"
    }},
    {{
      "message_number": 2,
      "score": 65,
      "reason": "Project update on key initiative",
      "category": "fyi"
    }}
  ]
}}

IMPORTANT: Return a priority object for every message number from 1 to {message_count}.
"""
        return prompt
    
    def _merge_priorities(
        self,
        messages: List[Dict[str, Any]],
        priorities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge AI priorities back into message objects.
        
        Args:
            messages: Original message dicts
            priorities: AI-generated priorities
            
        Returns:
            Messages with priorities added
        """
        # Create lookup by message number
        priority_lookup = {
            p['message_number']: p
            for p in priorities
        }
        
        result = []
        for i, msg in enumerate(messages, 1):
            priority = priority_lookup.get(i, {
                "score": 50,
                "reason": "No priority assigned by AI",
                "category": "fyi"
            })
            
            result.append({
                **msg,
                "priority_score": priority['score'],
                "priority_reason": priority['reason'],
                "category": priority['category']
            })
        
        return result
    
    def _message_obj_to_dict(self, message_obj) -> Dict[str, Any]:
        """
        Convert SQLAlchemy message object to dict for processing.
        
        Args:
            message_obj: SlackMessage object
            
        Returns:
            Message dict
        """
        return {
            "db_id": message_obj.id,
            "message_id": message_obj.message_id,
            "channel_id": message_obj.channel_id,
            "channel_name": message_obj.channel_name,
            "user_id": message_obj.user_id,
            "user_name": message_obj.user_name,
            "text": message_obj.text,
            "timestamp": message_obj.timestamp.isoformat() if message_obj.timestamp else None,
            "thread_ts": message_obj.thread_ts,
            "is_thread_parent": message_obj.is_thread_parent,
            "reply_count": message_obj.reply_count,
            "mentioned_users": message_obj.mentioned_users,
            "has_files": message_obj.has_files,
            "reactions": message_obj.reactions,
            "reaction_count": message_obj.reaction_count
        }

