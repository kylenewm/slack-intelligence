"""
Notion integration service for creating tasks from Slack messages.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)


class NotionTaskExtractor:
    """Extract actionable tasks from messages"""
    
    @staticmethod
    def extract_task_from_message(message: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        Extract task from a message.
        
        Args:
            message: Message dict with text, user_name, channel_name
            
        Returns:
            Task dict with title and description, or None
        """
        text = message.get('text', '')
        user_name = message.get('user_name', 'Unknown')
        channel_name = message.get('channel_name', 'Unknown')
        priority_score = message.get('priority_score', 0)
        
        # Don't create tasks for low priority messages
        if priority_score < 70:
            return None
        
        # Extract task (first line or whole text)
        lines = text.split('\n')
        title = lines[0][:200] if lines else 'Task from Slack'  # Increased from 100 to 200
        
        # Create description with full context
        description = f"""📧 **From:** {user_name}
📱 **Channel:** #{channel_name}
🎯 **Priority Score:** {priority_score}/100
🔥 **Reason:** {message.get('priority_reason', 'N/A')}

---

**Full Message:**
{text}

---

⏰ **Received:** {message.get('timestamp', 'Unknown time')}
🔗 **Slack Link:** slack:///archives/{channel_name}"""
        
        return {
            'title': title,
            'description': description,
            'priority_score': priority_score,
            'user_name': user_name,
            'channel_name': channel_name
        }


class NotionClient:
    """Notion API client for managing tasks"""
    
    def __init__(self, api_key: str, database_id: str):
        """
        Initialize Notion client.
        
        Args:
            api_key: Notion API key
            database_id: Notion database ID (the Slack Inbox database)
        """
        self.api_key = api_key
        self.database_id = database_id
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
    
    async def create_task(self, task: Dict[str, str]) -> Optional[str]:
        """
        Create a task in Notion database.
        
        Args:
            task: Task dict with title and description
            
        Returns:
            Task ID if successful, None otherwise
        """
        try:
            payload = {
                "parent": {"database_id": self.database_id},
                "properties": {
                    "Name": {
                        "title": [
                            {
                                "text": {
                                    "content": task['title']
                                }
                            }
                        ]
                    },
                    "Description": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": task['description']
                                }
                            }
                        ]
                    },
                    "From": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": task.get('user_name', 'Unknown')
                                }
                            }
                        ]
                    },
                    "Channel": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": f"#{task.get('channel_name', 'Unknown')}"
                                }
                            }
                        ]
                    },
                    "Score": {
                        "number": task['priority_score']
                    },
                    "Priority": {
                        "select": {
                            "name": self._get_priority_label(task['priority_score'])
                        }
                    },
                    "Source": {
                        "select": {
                            "name": "Slack"
                        }
                    },
                    "Status": {
                        "select": {
                            "name": "Not Started"
                        }
                    }
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/pages",
                    json=payload,
                    headers=self.headers,
                    timeout=10.0
                )
            
            if response.status_code == 200:
                result = response.json()
                task_id = result.get('id')
                logger.info(f"✅ Created Notion task: {task['title'][:50]}...")
                return task_id
            else:
                logger.error(f"❌ Notion API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating Notion task: {e}")
            return None
    
    async def query_tasks(self, filter_status: str = "Todo") -> List[Dict[str, Any]]:
        """
        Query existing tasks from Notion database.
        
        Args:
            filter_status: Status to filter by (default: "Todo")
            
        Returns:
            List of tasks
        """
        try:
            payload = {
                "filter": {
                    "property": "Status",
                    "select": {
                        "equals": filter_status
                    }
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/databases/{self.database_id}/query",
                    json=payload,
                    headers=self.headers,
                    timeout=10.0
                )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('results', [])
            else:
                logger.error(f"❌ Notion query error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error querying Notion: {e}")
            return []
    
    async def find_task_by_slack_message(self, message_id: str, channel_id: str) -> Optional[str]:
        """
        Find Notion page ID for a Slack message.
        
        Args:
            message_id: Slack message ID
            channel_id: Slack channel ID
            
        Returns:
            Notion page ID or None if not found
        """
        try:
            # Query for pages matching this Slack message
            # Note: This is a simplified search. In production, you might want to
            # add a custom "Slack Message ID" property to track this better
            payload = {
                "page_size": 100
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/databases/{self.database_id}/query",
                    json=payload,
                    headers=self.headers,
                    timeout=10.0
                )
            
            if response.status_code == 200:
                result = response.json()
                pages = result.get('results', [])
                
                # Search through pages for matching message
                # This is a best-effort match based on the description or title
                for page in pages:
                    props = page.get('properties', {})
                    # You might need to adjust this logic based on your Notion schema
                    # For now, we'll return the most recent page (simplified)
                    return page.get('id')
                
                logger.warning(f"No Notion page found for Slack message {message_id}")
                return None
            else:
                logger.error(f"❌ Error finding Notion task: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error finding Notion task: {e}")
            return None
    
    async def update_task_with_jira_link(
        self, 
        page_id: str, 
        jira_url: str, 
        jira_key: str
    ) -> bool:
        """
        Update existing Notion task with Jira ticket link.
        
        Args:
            page_id: Notion page ID
            jira_url: Full Jira ticket URL
            jira_key: Jira ticket key (e.g., PROJ-123)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {
                "properties": {
                    "Jira Ticket": {
                        "url": jira_url
                    },
                    "Jira Key": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": jira_key
                                }
                            }
                        ]
                    }
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.base_url}/pages/{page_id}",
                    json=payload,
                    headers=self.headers,
                    timeout=10.0
                )
            
            if response.status_code == 200:
                logger.info(f"✅ Updated Notion task with Jira link: {jira_key}")
                return True
            else:
                logger.error(f"❌ Failed to update Notion task: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating Notion task: {e}")
            return False
    
    @staticmethod
    def _get_priority_label(score: int) -> str:
        """Convert priority score to label"""
        if score >= 90:
            return "Critical"
        elif score >= 70:
            return "High"
        elif score >= 50:
            return "Medium"
        else:
            return "Low"


class NotionSyncService:
    """Service to sync Slack message insights to Notion"""
    
    def __init__(self, api_key: Optional[str] = None, database_id: Optional[str] = None):
        """
        Initialize Notion sync service.
        
        Args:
            api_key: Notion API key (from config)
            database_id: Notion database ID (from config)
        """
        self.enabled = api_key and database_id
        
        if self.enabled:
            self.client = NotionClient(api_key, database_id)
            self.extractor = NotionTaskExtractor()
        else:
            self.client = None
            self.extractor = None
            logger.info("ℹ️  Notion integration disabled (no API key configured)")
    
    async def sync_messages_to_notion(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Sync high-priority messages to Notion as tasks.
        
        Args:
            messages: List of message dicts to process
            
        Returns:
            Sync results dict
        """
        if not self.enabled:
            return {
                'status': 'disabled',
                'tasks_created': 0,
                'tasks_skipped': 0,
                'errors': 0
            }
        
        created = 0
        skipped = 0
        errors = 0
        
        logger.info(f"🔄 Syncing {len(messages)} messages to Notion...")
        
        for message in messages:
            try:
                # Extract task from message
                task = self.extractor.extract_task_from_message(message)
                
                if task is None:
                    skipped += 1
                    continue
                
                # Create task in Notion
                task_id = await self.client.create_task(task)
                
                if task_id:
                    created += 1
                else:
                    errors += 1
                
                # Rate limit: 3 requests per second for Notion
                await asyncio.sleep(0.4)
                
            except Exception as e:
                logger.error(f"❌ Error syncing message: {e}")
                errors += 1
        
        result = {
            'status': 'success' if errors == 0 else 'partial',
            'tasks_created': created,
            'tasks_skipped': skipped,
            'errors': errors
        }
        
        logger.info(f"✅ Notion sync complete: {created} created, {skipped} skipped, {errors} errors")
        
        return result
    
    async def get_notion_tasks(self) -> List[Dict[str, Any]]:
        """Get current tasks from Notion"""
        if not self.enabled:
            return []
        
        return await self.client.query_tasks()
