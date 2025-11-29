"""
AI-powered message prioritization with deterministic multipliers.

Hybrid approach:
1. LLM scores message CONTENT only (0-100)
2. Deterministic multipliers applied for VIP people, channels
3. Diminishing returns formula prevents scores from exceeding 100
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

# =============================================================================
# SCORING MULTIPLIERS (Deterministic)
# =============================================================================
VIP_MULTIPLIER = 2.0               # 2x boost for VIP people
MENTION_MULTIPLIER = 2.0           # 2x boost for direct @mentions
PRIORITY_CHANNEL_MULTIPLIER = 1.5  # 1.5x boost for priority channels
MUTED_CHANNEL_MULTIPLIER = 0.5     # 0.5x penalty for muted channels


class MessagePrioritizer:
    """AI-powered message prioritization with deterministic multipliers"""
    
    def __init__(self, user_preferences: Dict[str, Any] = None):
        """
        Initialize prioritizer.
        
        Args:
            user_preferences: Dict with key_people, key_channels, mute_channels
        """
        self.cache = CacheService()
        
        # Load preferences: passed in > database > env file fallback
        if user_preferences:
            self.user_preferences = user_preferences
        else:
            # Try database first
            db_prefs = self.cache.get_user_preferences("default")
            if db_prefs and any([db_prefs.get('key_people'), db_prefs.get('key_channels'), db_prefs.get('mute_channels')]):
                self.user_preferences = db_prefs
            else:
                # Fallback to env file
                self.user_preferences = settings.get_user_preferences()
        
        # Normalize preferences for matching (lowercase)
        self.vip_people = [p.lower().strip() for p in self.user_preferences.get('key_people', [])]
        self.priority_channels = [c.lower().strip() for c in self.user_preferences.get('key_channels', [])]
        self.muted_channels = [c.lower().strip() for c in self.user_preferences.get('mute_channels', [])]
        
        logger.info(f"📋 Loaded preferences: VIPs={self.vip_people}, Priority={self.priority_channels}, Muted={self.muted_channels}")
    
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
                
                # Merge priorities back into messages, then apply multipliers
                merged = self._merge_priorities(messages, priorities)
                return self._apply_multipliers(merged)
                
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
        Build the prioritization prompt - CONTENT ONLY.
        
        The LLM scores based on message content/urgency.
        VIP/channel multipliers are applied separately after LLM scoring.
        
        Args:
            messages_text: Formatted messages
            message_count: Number of messages
            
        Returns:
            Complete prompt string
        """
        prompt = f"""Score these {message_count} Slack messages by CONTENT URGENCY only (0-100).

DO NOT consider who sent the message or which channel. Only score the MESSAGE CONTENT.

SCORING GUIDELINES:

🚨 URGENT (90-100):
• Production issues, outages, critical errors
• Explicit deadlines: "today", "EOD", "ASAP", "urgent"
• Direct blocking requests: "waiting on you", "can you"
• Emergencies or crises

🔥 HIGH (70-89):
• Important decisions being discussed
• Action items or deliverables mentioned
• Technical issues requiring attention
• Meeting requests or deadlines

📋 MEDIUM (50-69):
• Project updates or status reports
• Informational announcements
• Relevant team discussions
• Questions that aren't blocking

⬇️ LOW (0-49):
• Casual chat, social conversations
• Off-topic discussions
• Jokes, emoji reactions, "thanks"
• Coffee/lunch/watercooler talk

MESSAGES:
{messages_text}

Return JSON:
{{
  "priorities": [
    {{"message_number": 1, "score": 95, "reason": "Production outage", "category": "needs_response"}},
    {{"message_number": 2, "score": 25, "reason": "Casual chat", "category": "low_priority"}}
  ]
}}

Return exactly {message_count} priorities.
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
    
    def _apply_multipliers(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply deterministic multipliers to LLM base scores.
        
        Uses diminishing returns formula so scores approach but never exceed 100.
        
        Multipliers applied in order:
        1. Muted channel (0.5x) - reduces noise first
        2. Priority channel (1.5x) - boosts important channels
        3. Direct @mention (2.0x) - someone explicitly asked for you
        4. VIP person (2.0x) - VIP has final say
        
        Args:
            messages: Messages with LLM base scores
            
        Returns:
            Messages with adjusted scores and updated reasons
        """
        adjusted = []
        
        # Get your user ID for mention detection (try multiple env vars)
        import os
        your_user_id = (
            os.getenv('YOUR_USER_ID_PERSONAL') or 
            os.getenv('YOUR_USER_ID') or 
            os.getenv('SLACK_ALERT_USER_ID') or 
            ''
        )
        
        for msg in messages:
            base_score = msg['priority_score']
            score = base_score
            adjustments = []
            
            user_name = msg.get('user_name', '').lower().strip()
            channel_name = msg.get('channel_name', '').lower().strip()
            text = msg.get('text', '')
            
            # Check if you're directly mentioned
            is_mentioned = your_user_id and f'<@{your_user_id}>' in text
            
            # 1. Apply muted channel penalty (BUT skip if you're @mentioned - that's important!)
            if channel_name in self.muted_channels:
                if is_mentioned:
                    # Skip muted penalty - someone explicitly asked for you
                    adjustments.append("muted channel skipped (@mention override)")
                else:
                    score = self._apply_diminishing_multiplier(score, MUTED_CHANNEL_MULTIPLIER)
                    adjustments.append(f"muted channel ×{MUTED_CHANNEL_MULTIPLIER}")
            
            # 2. Apply priority channel boost
            elif channel_name in self.priority_channels:
                score = self._apply_diminishing_multiplier(score, PRIORITY_CHANNEL_MULTIPLIER)
                adjustments.append(f"priority channel ×{PRIORITY_CHANNEL_MULTIPLIER}")
            
            # 3. Apply direct @mention boost (if you're mentioned)
            if is_mentioned:
                score = self._apply_diminishing_multiplier(score, MENTION_MULTIPLIER)
                adjustments.append(f"@mention ×{MENTION_MULTIPLIER}")
            
            # 4. Apply VIP boost last (highest precedence)
            if user_name in self.vip_people:
                score = self._apply_diminishing_multiplier(score, VIP_MULTIPLIER)
                adjustments.append(f"VIP ×{VIP_MULTIPLIER}")
            
            # Round to integer
            final_score = round(score)
            
            # Update reason if adjustments were made
            reason = msg['priority_reason']
            if adjustments:
                adjustment_str = ", ".join(adjustments)
                reason = f"{reason} [Adjusted: {adjustment_str}, base={base_score}→{final_score}]"
                logger.debug(f"   📊 {user_name} in #{channel_name}: {base_score} → {final_score} ({adjustment_str})")
            
            # Update category based on final score
            category = self._score_to_category(final_score)
            
            adjusted.append({
                **msg,
                "priority_score": final_score,
                "priority_reason": reason,
                "category": category
            })
        
        return adjusted
    
    def _apply_diminishing_multiplier(self, score: float, multiplier: float) -> float:
        """
        Apply a multiplier with diminishing returns as score approaches 100.
        
        Formula for boost (multiplier > 1):
            effective_boost = (multiplier - 1) * score * (headroom / 100)
            new_score = score + effective_boost
        
        For penalty (multiplier < 1):
            Simply multiply (penalties don't need diminishing returns)
        
        Examples with VIP 2.0x:
            score=50: 50 + 1.0*50*(50/100) = 50 + 25 = 75
            score=70: 70 + 1.0*70*(30/100) = 70 + 21 = 91
            score=90: 90 + 1.0*90*(10/100) = 90 + 9 = 99
        
        Args:
            score: Current score (0-100)
            multiplier: Multiplier to apply
            
        Returns:
            Adjusted score (naturally capped at 100)
        """
        if multiplier == 1.0:
            return score
        
        if multiplier < 1.0:
            # Penalty: just multiply directly
            return score * multiplier
        
        # Boost with diminishing returns
        boost_factor = multiplier - 1.0  # 2.0 → 1.0 (100% boost attempt)
        headroom = 100 - score  # How much room to grow
        effective_boost = boost_factor * score * (headroom / 100)
        
        return score + effective_boost
    
    def _score_to_category(self, score: int) -> str:
        """Convert score to category."""
        if score >= 80:
            return "needs_response"
        elif score >= 70:
            return "high_priority"
        elif score >= 50:
            return "fyi"
        else:
            return "low_priority"
    
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

