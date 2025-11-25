"""
Slack Block Kit Builder for Interactive Proposals.
"""

from typing import Dict, Any, Optional

def create_proposal_blocks(
    message: Dict[str, Any],
    research_summary: str,
    ticket_type: str,
    priority_score: int
) -> list:
    """
    Create an interactive Slack message proposing a ticket.
    """
    text = message.get("text", "")
    user = message.get("user_name", "Unknown")
    channel = message.get("channel_name", "Unknown")
    
    # Color based on priority (Slack doesn't support color in blocks, but we can use emoji)
    emoji = "🔴" if priority_score >= 90 else "🟡" if priority_score >= 70 else "🟢"
    
    # Truncate summary
    summary_preview = research_summary[:200] + "..." if len(research_summary) > 200 else research_summary

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} AI Suggested Ticket: {ticket_type.title()}",
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"From *{user}* in *#{channel}* | Score: {priority_score}"
                }
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{text}*"
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*🤖 AI Research:*\n{summary_preview}"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✅ Create Ticket",
                        "emoji": True
                    },
                    "style": "primary",
                    "value": "create_ticket",
                    "action_id": "create_ticket_action"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✏️ Edit Details",
                        "emoji": True
                    },
                    "value": "edit_ticket",
                    "action_id": "edit_ticket_action"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "❌ Ignore",
                        "emoji": True
                    },
                    "style": "danger",
                    "value": "ignore_ticket",
                    "action_id": "ignore_ticket_action"
                }
            ]
        }
    ]
    
    return blocks

