"""
Configuration module for Slack Intelligence.
Loads environment variables and stores application settings.
"""

import os
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings and configuration."""
    
    # Base Directory
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Slack API Configuration
    SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")  # Bot User OAuth Token
    SLACK_USER_TOKEN: str = os.getenv("SLACK_USER_TOKEN", "")  # User OAuth Token (for search)
    SLACK_SIGNING_SECRET: str = os.getenv("SLACK_SIGNING_SECRET", "")
    SLACK_WORKSPACE_ID: str = os.getenv("SLACK_WORKSPACE_ID", "")
    
    # OpenAI API
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Application Settings
    APP_NAME: str = "Slack Intelligence"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    API_PORT: int = int(os.getenv("API_PORT", "8000"))  # Configurable port (default 8000)
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")  # Configurable host
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR}/slack_intelligence.db"
    )
    
    # Sync Settings
    SYNC_INTERVAL_MINUTES: int = int(os.getenv("SYNC_INTERVAL_MINUTES", "15"))
    DEFAULT_HOURS_LOOKBACK: int = int(os.getenv("DEFAULT_HOURS_LOOKBACK", "24"))
    MAX_MESSAGES_PER_SYNC: int = int(os.getenv("MAX_MESSAGES_PER_SYNC", "500"))
    
    # Auto-sync Settings
    AUTO_SYNC_ENABLED: bool = os.getenv("AUTO_SYNC_ENABLED", "false").lower() == "true"
    WORK_HOURS_ONLY: bool = os.getenv("WORK_HOURS_ONLY", "false").lower() == "true"
    
    # Alert Settings
    SLACK_ALERT_USER_ID: str = os.getenv("SLACK_ALERT_USER_ID", "")
    
    # AI Processing Settings
    PRIORITIZATION_MODEL: str = os.getenv("PRIORITIZATION_MODEL", "gpt-4o-mini")
    PRIORITIZATION_BATCH_SIZE: int = int(os.getenv("PRIORITIZATION_BATCH_SIZE", "50"))
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    
    # Priority Thresholds
    URGENT_THRESHOLD: int = 90  # Score >= 90 = urgent
    HIGH_PRIORITY_THRESHOLD: int = 70  # Score >= 70 = high priority
    MEDIUM_PRIORITY_THRESHOLD: int = 50  # Score >= 50 = medium priority
    
    # User Preferences (can be moved to database later)
    KEY_PEOPLE: List[str] = os.getenv("KEY_PEOPLE", "").split(",") if os.getenv("KEY_PEOPLE") else []
    KEY_CHANNELS: List[str] = os.getenv("KEY_CHANNELS", "").split(",") if os.getenv("KEY_CHANNELS") else []
    KEY_KEYWORDS: List[str] = os.getenv("KEY_KEYWORDS", "").split(",") if os.getenv("KEY_KEYWORDS") else []
    
    # Auto-archive patterns
    MUTE_CHANNELS: List[str] = os.getenv("MUTE_CHANNELS", "").split(",") if os.getenv("MUTE_CHANNELS") else []
    
    # Notion Integration
    NOTION_API_KEY: str = os.getenv("NOTION_API_KEY", "")
    NOTION_DATABASE_ID: str = os.getenv("NOTION_DATABASE_ID", "")
    NOTION_SYNC_ENABLED: bool = os.getenv("NOTION_SYNC_ENABLED", "false").lower() == "true"
    NOTION_MIN_PRIORITY_SCORE: int = int(os.getenv("NOTION_MIN_PRIORITY_SCORE", "70"))
    
    # Exa Search Integration
    EXA_API_KEY: str = os.getenv("EXA_API_KEY", "")
    
    # Vector Database (Pinecone)
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX: str = os.getenv("PINECONE_INDEX", "traverse-ai-memory")
    
    #     Jira Integration
    JIRA_API_KEY: str = os.getenv("JIRA_API_KEY", "")
    JIRA_EMAIL: str = os.getenv("JIRA_EMAIL", "")
    JIRA_DOMAIN: str = os.getenv("JIRA_DOMAIN", "")
    JIRA_PROJECT_KEY: str = os.getenv("JIRA_PROJECT_KEY", "")
    JIRA_SYNC_ENABLED: bool = os.getenv("JIRA_SYNC_ENABLED", "false").lower() == "true"
    
    # CORS Settings (for future web UI)
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate that required settings are present.
        
        Returns:
            bool: True if all required settings are valid
        """
        errors = []
        
        if not cls.SLACK_BOT_TOKEN:
            errors.append("SLACK_BOT_TOKEN not set")
        
        if not cls.SLACK_USER_TOKEN:
            errors.append("SLACK_USER_TOKEN not set")
        
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY not set")
        
        if errors:
            print("❌ Configuration errors:")
            for error in errors:
                print(f"   - {error}")
            return False
        
        print("✅ Configuration validated")
        return True
    
    @classmethod
    def get_user_preferences(cls) -> dict:
        """Get user preferences as a dict for AI context"""
        return {
            "key_people": [p.strip() for p in cls.KEY_PEOPLE if p.strip()],
            "key_channels": [c.strip() for c in cls.KEY_CHANNELS if c.strip()],
            "key_keywords": [k.strip() for k in cls.KEY_KEYWORDS if k.strip()],
            "mute_channels": [m.strip() for m in cls.MUTE_CHANNELS if m.strip()]
        }


settings = Settings()

