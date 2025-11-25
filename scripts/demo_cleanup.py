#!/usr/bin/env python3
"""
Demo Cleanup Script
Resets the database and clears demo data for clean demo runs.

Usage:
    python scripts/demo_cleanup.py          # Clean demo messages only
    python scripts/demo_cleanup.py --all    # Clean everything (full reset)
"""

import sys
import argparse
from pathlib import Path
import sqlite3
import os

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database.db import init_db, get_db_session
from backend.database.models import SlackMessage, MessageInsight, SyncLog

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None


def print_header(title: str):
    """Print header"""
    if console:
        console.print(Panel(
            f"[bold cyan]{title}[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED
        ))
    else:
        print("\n" + "="*70)
        print(f"🧹 {title}")
        print("="*70 + "\n")


def print_success(message: str):
    """Print success message"""
    if console:
        console.print(f"[green]✅[/green] {message}")
    else:
        print(f"✅ {message}")


def cleanup_demo_messages():
    """Remove demo messages from database"""
    print("Cleaning demo messages...")
    
    with get_db_session() as session:
        # Find demo messages
        demo_msgs = session.query(SlackMessage).filter(
            SlackMessage.message_id.like('demo_%')
        ).all()
        
        ai_demo_msgs = session.query(SlackMessage).filter(
            SlackMessage.message_id.like('ai_demo_%')
        ).all()
        
        all_demo_msgs = demo_msgs + ai_demo_msgs
        
        # Delete associated insights first (due to foreign key)
        for msg in all_demo_msgs:
            session.query(MessageInsight).filter(
                MessageInsight.message_id == msg.id
            ).delete()
        
        # Delete demo messages
        deleted_messages = len(demo_msgs)
        deleted_ai = len(ai_demo_msgs)
        
        for msg in all_demo_msgs:
            session.delete(msg)
        
        session.commit()
        
        total_deleted = deleted_messages + deleted_ai
        print_success(f"Deleted {total_deleted} demo messages")
        return total_deleted


def cleanup_all():
    """Clean everything - full reset"""
    print("Performing full cleanup...")
    
    with get_db_session() as session:
        # Delete all messages
        deleted_messages = session.query(SlackMessage).delete()
        
        # Delete all insights
        deleted_insights = session.query(MessageInsight).delete()
        
        # Delete all sync logs
        deleted_logs = session.query(SyncLog).delete()
        
        session.commit()
        
        print_success(f"Deleted {deleted_messages} messages")
        print_success(f"Deleted {deleted_insights} insights")
        print_success(f"Deleted {deleted_logs} sync logs")
        
        return deleted_messages + deleted_insights + deleted_logs


def reset_database():
    """Drop and recreate database"""
    print("Resetting database...")
    
    from backend.config import settings
    
    # Get database path
    db_url = settings.DATABASE_URL
    if db_url.startswith('sqlite:///'):
        db_path = db_url.replace('sqlite:///', '')
        
        if os.path.exists(db_path):
            os.remove(db_path)
            print_success(f"Removed database file: {db_path}")
        
        # Reinitialize
        init_db()
        print_success("Database reinitialized")
    else:
        print("⚠️  Cannot reset non-SQLite database")


def main():
    """Main cleanup function"""
    parser = argparse.ArgumentParser(
        description="Clean up demo data for fresh demo runs"
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Clean everything (full reset)'
    )
    
    parser.add_argument(
        '--reset-db',
        action='store_true',
        help='Drop and recreate database (destructive!)'
    )
    
    args = parser.parse_args()
    
    print_header("Demo Cleanup")
    
    if args.reset_db:
        confirm = input("⚠️  This will DELETE ALL DATA. Are you sure? (yes/no): ")
        if confirm.lower() == 'yes':
            reset_database()
        else:
            print("Cancelled.")
            return
    
    if args.all:
        confirm = input("⚠️  This will delete ALL messages. Continue? (yes/no): ")
        if confirm.lower() == 'yes':
            cleanup_all()
        else:
            print("Cancelled.")
            return
    else:
        deleted = cleanup_demo_messages()
        if deleted == 0:
            print("No demo messages found to clean.")
        else:
            print_success(f"Cleanup complete! Deleted {deleted} demo messages.")
    
    print("\n✅ Demo cleanup complete! Ready for a fresh demo run.")


if __name__ == "__main__":
    main()

