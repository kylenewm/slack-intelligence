"""
Memory Service - RAG Layer using Pinecone.
Stores and retrieves semantic context (Slack history, codebase snippets) to power the AI.
"""

import logging
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec

from ..config import settings

logger = logging.getLogger(__name__)

class MemoryService:
    """
    Manages the Vector Database (Pinecone) for RAG.
    """
    
    def __init__(self):
        self.enabled = bool(settings.PINECONE_API_KEY)
        self.openai_client = None
        self.pc = None
        self.index = None
        
        if not self.enabled:
            logger.warning("PINECONE_API_KEY not set. Memory Service disabled.")
            return

        try:
            # Init OpenAI
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Init Pinecone
            self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
            
            # Check/Create Index
            index_name = settings.PINECONE_INDEX
            if index_name not in [i.name for i in self.pc.list_indexes()]:
                logger.info(f"Creating Pinecone index: {index_name}...")
                self.pc.create_index(
                    name=index_name,
                    dimension=1536, # openai text-embedding-3-small
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                # Wait for initialization
                while not self.pc.describe_index(index_name).status['ready']:
                    time.sleep(1)
            
            self.index = self.pc.Index(index_name)
            logger.info(f"✅ Memory Service initialized (Index: {index_name})")
            
        except Exception as e:
            logger.error(f"Failed to initialize Memory Service: {e}")
            self.enabled = False

    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        if not self.openai_client:
            return []
            
        text = text.replace("\n", " ")
        return self.openai_client.embeddings.create(
            input=[text], model="text-embedding-3-small"
        ).data[0].embedding

    def upsert_memory(self, id: str, text: str, metadata: Dict[str, Any]) -> bool:
        """
        Store a memory in Pinecone.
        
        Args:
            id: Unique ID (e.g., "msg_12345")
            text: The content to embed
            metadata: Additional info (user, channel, timestamp)
        """
        if not self.enabled or not self.index:
            return False
            
        try:
            vector = self._get_embedding(text)
            
            # Pinecone metadata values must be strings, numbers, bools, or lists of strings
            clean_meta = {k: v for k, v in metadata.items() if v is not None}
            clean_meta["text"] = text # Store original text in metadata for retrieval
            
            self.index.upsert(vectors=[(id, vector, clean_meta)])
            logger.info(f"🧠 Memorized: {id}")
            return True
        except Exception as e:
            logger.error(f"Error upserting memory {id}: {e}")
            return False

    def search_memory(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories for a query.
        """
        if not self.enabled or not self.index:
            return []
            
        try:
            vector = self._get_embedding(query)
            
            results = self.index.query(
                vector=vector,
                top_k=top_k,
                include_metadata=True
            )
            
            memories = []
            for match in results.matches:
                memories.append({
                    "id": match.id,
                    "score": match.score,
                    "text": match.metadata.get("text", ""),
                    "metadata": match.metadata
                })
                
            return memories
        except Exception as e:
            logger.error(f"Error searching memory: {e}")
            return []

    def index_message(self, message: Dict[str, Any]) -> bool:
        """
        Helper to index a Slack message.
        """
        if not message.get("text"):
            return False
            
        text = f"[{message.get('user_name', 'Unknown')}] in #{message.get('channel_name', 'Unknown')}: {message.get('text')}"
        
        metadata = {
            "type": "slack_message",
            "user": message.get("user_name", "Unknown"),
            "channel": message.get("channel_name", "Unknown"),
            "timestamp": str(message.get("timestamp", "")),
            "thread_ts": str(message.get("thread_ts", ""))
        }
        
        return self.upsert_memory(
            id=f"msg_{message.get('message_id')}",
            text=text,
            metadata=metadata
        )

