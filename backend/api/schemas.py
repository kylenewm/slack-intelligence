"""
Pydantic schemas for API requests/responses.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class MessageDetail(BaseModel):
    """Message details for API responses"""
    id: int
    message_id: str
    channel_id: str
    channel_name: Optional[str]
    user_id: str
    user_name: Optional[str]
    text: str
    timestamp: Optional[str]
    priority_score: Optional[int]
    priority_reason: Optional[str]
    category: Optional[str]
    thread_ts: Optional[str]
    is_thread_parent: bool = False
    reply_count: int = 0
    reactions: Optional[List[Dict]] = []
    has_files: bool = False
    archived: bool = False
    read: bool = False
    link: str
    
    class Config:
        from_attributes = True


class SmartInboxResponse(BaseModel):
    """Response for smart inbox endpoints"""
    view: str
    total: int
    messages: List[MessageDetail]
    generated_at: datetime


class FetchStats(BaseModel):
    """Fetch statistics"""
    channels_synced: int
    messages_fetched: int
    new_messages: int
    skipped_cached: int
    errors: List[Dict[str, Any]]


class PrioritizationStats(BaseModel):
    """Prioritization statistics"""
    total_messages: int
    prioritized: int
    errors: List[Dict[str, Any]]


class SyncResponse(BaseModel):
    """Response for sync endpoint"""
    status: str
    duration_seconds: float
    fetch: FetchStats
    prioritization: PrioritizationStats
    timestamp: str


class SearchResponse(BaseModel):
    """Response for search endpoint"""
    query: str
    total: int
    results: List[MessageDetail]


class StatsResponse(BaseModel):
    """System statistics"""
    time_window: str
    total_messages: int
    by_category: Dict[str, int]
    latest_sync: Optional[Dict[str, Any]]
    generated_at: str

