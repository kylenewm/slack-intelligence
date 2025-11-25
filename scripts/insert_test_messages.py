#!/usr/bin/env python3
"""
Insert test messages directly into the database for testing dashboard
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone
from backend.database.db import get_db
from backend.database.models import SlackMessage

def insert_test_messages():
    """Insert diverse test messages for dashboard testing"""
    
    test_messages = [
        {
            "message_id": "test_msg_001",
            "channel_id": "C123TEST",
            "channel_name": "engineering-alerts",
            "user_id": "U123USER",
            "user_name": "PagerDuty Bot",
            "text": "🚨 ALERT: Slack API Rate Limit Exceeded (429). Ingestion worker #3 has crashed. We are missing the Retry-After header in the response. Queue backing up.",
            "timestamp": datetime.now(timezone.utc),
            "priority_score": 98,
            "category": "needs_response",
            "priority_reason": "Critical ingestion failure. Directly affects core value prop (real-time). Known issue with rate limits.",
        },
        {
            "message_id": "test_msg_002",
            "channel_id": "C123TEST",
            "channel_name": "product-feedback",
            "user_id": "U124USER",
            "user_name": "Sarah Product",
            "text": "Enterprise customer 'TechCorp' is complaining that their Notion pages look broken when synced. The rich text blocks from Slack aren't converting properly - seeing raw JSON instead of formatting.",
            "timestamp": datetime.now(timezone.utc),
            "priority_score": 85,
            "category": "high_priority",
            "priority_reason": "Customer-facing quality issue with a core integration (Notion). Risk of churn for enterprise account.",
        },
        {
            "message_id": "test_msg_003",
            "channel_id": "C123TEST",
            "channel_name": "architecture",
            "user_id": "U125USER",
            "user_name": "Alex Architect",
            "text": "We need to decide on a vector database for the new 'Similar Ticket' feature. Should we stick with pgvector since we're already on Postgres, or move to Pinecone for better scaling? Need a decision by Friday.",
            "timestamp": datetime.now(timezone.utc),
            "priority_score": 92,
            "category": "needs_response",
            "priority_reason": "Strategic architecture decision blocking a key roadmap feature. Time-sensitive (Friday deadline).",
        },
        {
            "message_id": "test_msg_004",
            "channel_id": "C123TEST",
            "channel_name": "general",
            "user_id": "U126USER",
            "user_name": "Emma HR",
            "text": "Reminder: Open enrollment for health benefits ends this Friday. Please submit your forms via Rippling.",
            "timestamp": datetime.now(timezone.utc),
            "priority_score": 60,
            "category": "fyi",
            "priority_reason": "Important deadline for employees, but not product-critical. Informational.",
        },
        {
            "message_id": "test_msg_005",
            "channel_id": "C123TEST",
            "channel_name": "random",
            "user_id": "U127USER",
            "user_name": "Chris Dev",
            "text": "Has anyone tried the new Cursor AI editor? The codebase context feature looks pretty similar to what we're building.",
            "timestamp": datetime.now(timezone.utc),
            "priority_score": 45,
            "category": "low_priority",
            "priority_reason": "Casual tech discussion. Relevant to industry but not actionable work.",
        },
        {
            "message_id": "test_msg_006",
            "channel_id": "DM_TEST",
            "channel_name": "Direct Message",
            "user_id": "U128USER",
            "user_name": "Jordan CTO",
            "text": "Can you review the PRD for the 'Context Engine' v2? I want to make sure we're capturing enough metadata for the RAG pipeline before we start engineering.",
            "timestamp": datetime.now(timezone.utc),
            "priority_score": 95,
            "category": "needs_response",
            "priority_reason": "Direct request from CTO about a core roadmap item. High urgency and strategic importance.",
        },
    ]
    
    print("🔧 Inserting test messages into database...")
    
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # Clear existing test messages
        existing = db.query(SlackMessage).filter(
            SlackMessage.message_id.like('test_msg_%')
        ).all()
        
        if existing:
            print(f"🗑️  Clearing {len(existing)} existing test messages...")
            for msg in existing:
                db.delete(msg)
            db.commit()
        
        # Insert new test messages
        for msg_data in test_messages:
            message = SlackMessage(**msg_data)
            db.add(message)
        
        db.commit()
        print(f"✅ Successfully inserted {len(test_messages)} test messages!")
        print("\n📊 Messages by priority:")
        print(f"   🔴 Needs Response: {sum(1 for m in test_messages if m['priority_score'] >= 90)}")
        print(f"   🟡 High Priority: {sum(1 for m in test_messages if 70 <= m['priority_score'] < 90)}")
        print(f"   🟢 FYI: {sum(1 for m in test_messages if 50 <= m['priority_score'] < 70)}")
        print(f"   ⚪ Low Priority: {sum(1 for m in test_messages if m['priority_score'] < 50)}")
        print("\n🌐 Dashboard: http://localhost:8501")
        print("📡 API Docs: http://localhost:8000/docs")
    finally:
        db.close()

if __name__ == "__main__":
    insert_test_messages()

