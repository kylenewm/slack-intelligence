"""
Database models for Slack Intelligence.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .db import Base


class SlackMessage(Base):
    """Slack message storage with AI analysis"""
    __tablename__ = "slack_messages"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Slack identifiers
    message_id = Column(String, unique=True, index=True, nullable=False)  # Slack message timestamp
    channel_id = Column(String, index=True, nullable=False)
    channel_name = Column(String)
    user_id = Column(String, index=True)
    user_name = Column(String)
    
    # Message content
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)
    
    # Thread information
    thread_ts = Column(String, index=True)  # Parent thread timestamp
    is_thread_parent = Column(Boolean, default=False)
    reply_count = Column(Integer, default=0)
    
    # AI analysis (denormalized for quick access)
    priority_score = Column(Integer, index=True)  # 0-100
    priority_reason = Column(Text)
    category = Column(String, index=True)  # "needs_response", "high_priority", "fyi", "low_priority"
    
    # Message metadata
    has_reactions = Column(Boolean, default=False)
    reaction_count = Column(Integer, default=0)
    reactions = Column(JSON)  # Store reaction details
    mentioned_users = Column(JSON)  # List of user IDs mentioned
    has_files = Column(Boolean, default=False)
    files = Column(JSON)  # File attachments
    
    # Embeddings for semantic search (optional)
    embedding = Column(JSON)  # Store as JSON array
    
    # Status tracking
    archived = Column(Boolean, default=False, index=True)
    read = Column(Boolean, default=False, index=True)
    snoozed_until = Column(DateTime)
    
    # Metadata
    raw_data = Column(JSON)  # Store full Slack API response
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    insights = relationship("MessageInsight", back_populates="message", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<SlackMessage {self.message_id} from {self.user_name} in {self.channel_name}>"


class MessageInsight(Base):
    """AI-generated insights and analysis for messages"""
    __tablename__ = "message_insights"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("slack_messages.id"), nullable=False)
    
    # AI analysis
    priority_score = Column(Integer, nullable=False)
    priority_reason = Column(Text)
    category = Column(String)
    
    # Extracted information
    action_items = Column(JSON)  # List of action items extracted
    summary = Column(Text)  # For long threads
    sentiment = Column(String)  # positive, negative, neutral
    urgency = Column(String)  # immediate, today, this_week, none
    
    # AI model info
    model_name = Column(String, default="gpt-4o-mini")
    token_count = Column(Integer)
    cost_cents = Column(Float)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    message = relationship("SlackMessage", back_populates="insights")
    
    def __repr__(self):
        return f"<MessageInsight for message {self.message_id}: score={self.priority_score}>"


class UserPreference(Base):
    """User-specific preferences for prioritization"""
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    slack_user_id = Column(String, unique=True, nullable=False, index=True)
    
    # VIP lists
    key_people = Column(JSON)  # List of user IDs to always prioritize
    key_channels = Column(JSON)  # List of channel IDs to prioritize
    key_keywords = Column(JSON)  # List of keywords/topics to prioritize
    
    # Auto-actions
    auto_archive_patterns = Column(JSON)  # Patterns to auto-archive
    mute_channels = Column(JSON)  # Channels to de-prioritize
    mute_users = Column(JSON)  # Users to de-prioritize
    
    # Notification preferences
    notify_on_urgent = Column(Boolean, default=True)
    notify_on_mentions = Column(Boolean, default=True)
    
    # Learning from feedback
    manual_priority_overrides = Column(JSON)  # Track when user changes priorities
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<UserPreference for {self.slack_user_id}>"


class SyncLog(Base):
    """Track sync operations for monitoring"""
    __tablename__ = "sync_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Sync details
    sync_type = Column(String, nullable=False)  # "scheduled", "manual", "initial"
    channels_synced = Column(JSON)  # List of channel IDs
    hours_lookback = Column(Integer)
    
    # Results
    messages_fetched = Column(Integer, default=0)
    new_messages = Column(Integer, default=0)
    messages_prioritized = Column(Integer, default=0)
    errors = Column(JSON)  # List of error details
    
    # Performance
    duration_seconds = Column(Float)
    ai_cost_cents = Column(Float)
    
    # Status
    status = Column(String, nullable=False)  # "success", "partial", "failed"
    error_message = Column(Text)
    
    # Metadata
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    
    def __repr__(self):
        return f"<SyncLog {self.sync_type} at {self.started_at}: {self.status}>"

