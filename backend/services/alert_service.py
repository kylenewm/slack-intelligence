"""
Alert Service - Sends instant Slack DM alerts for critical messages.
"""

import logging
from typing import Dict, Any, List
from slack_sdk.web.async_client import AsyncWebClient

from ..config import settings

logger = logging.getLogger(__name__)


class AlertService:
    """Send instant Slack DM alerts for high-priority messages"""
    
    def __init__(self):
        self.slack_client = AsyncWebClient(token=settings.SLACK_BOT_TOKEN)
        self.alert_user_id = settings.SLACK_ALERT_USER_ID
        self.critical_threshold = 90  # Score >= 90 triggers instant alert
    
    async def send_critical_alerts(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send instant DM alerts for critical messages.
        
        Args:
            messages: List of prioritized messages
            
        Returns:
            Dict with alert results
        """
        if not self.alert_user_id:
            logger.warning("⚠️  SLACK_ALERT_USER_ID not configured, skipping alerts")
            return {"status": "disabled", "alerts_sent": 0}
        
        # Filter critical messages
        critical_messages = [
            msg for msg in messages 
            if msg.get('priority_score', 0) >= self.critical_threshold
        ]
        
        if not critical_messages:
            return {"status": "success", "alerts_sent": 0}
        
        logger.info(f"🚨 Sending {len(critical_messages)} critical alerts...")
        
        alerts_sent = 0
        errors = []
        
        for message in critical_messages:
            try:
                await self._send_dm_alert(message)
                alerts_sent += 1
            except Exception as e:
                logger.error(f"❌ Failed to send alert for message {message.get('id')}: {e}")
                errors.append(str(e))
        
        logger.info(f"✅ Sent {alerts_sent} critical alerts")
        
        return {
            "status": "success" if not errors else "partial",
            "alerts_sent": alerts_sent,
            "errors": errors
        }
    
    async def _send_dm_alert(self, message: Dict[str, Any]) -> None:
        """Send a single DM alert for a critical message using Block Kit"""
        
        # Lazy import to avoid circular dependency
        from ..api.slack_blocks import create_proposal_blocks
        
        priority_score = message.get('priority_score', 0)
        text = message.get('text', '')
        
        # Create interactive blocks
        # Note: Research is not yet available at this stage of the pipeline
        blocks = create_proposal_blocks(
            message=message,
            research_summary="⚠️ Research pending... (Will be updated)",
            ticket_type="Critical Incident",
            priority_score=priority_score
        )
        
        # Send DM using Slack API
        response = await self.slack_client.chat_postMessage(
            channel=self.alert_user_id,
            text=f"🚨 CRITICAL: {text[:50]}...",  # Fallback text
            blocks=blocks,
            unfurl_links=False,
            unfurl_media=False
        )
        
        if not response.get('ok'):
            raise Exception(f"Slack API error: {response.get('error', 'Unknown error')}")
        
        logger.info(f"   ✅ Alert sent for message: {text[:50]}...")
