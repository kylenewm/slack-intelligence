"""
Backfill Memory Script.
Reads all historical Slack messages from SQLite and indexes them into Pinecone Vector DB.
Run this once to initialize the "Brain".
"""

import sys
import os
import asyncio
from pathlib import Path
from rich.console import Console
from rich.progress import track

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import SessionLocal
from backend.database.models import SlackMessage
from backend.services.memory_service import MemoryService

console = Console()

async def backfill():
    console.print("[bold cyan]🧠 Starting Memory Backfill...[/bold cyan]")
    
    # Init Service
    memory = MemoryService()
    if not memory.enabled:
        console.print("[red]❌ Memory Service not enabled. Check PINECONE_API_KEY.[/red]")
        return

    # Get Messages
    db = SessionLocal()
    try:
        messages = db.query(SlackMessage).all()
        console.print(f"Found {len(messages)} messages in database.")
        
        success_count = 0
        error_count = 0
        
        # Process Loop
        for msg in track(messages, description="Indexing messages..."):
            try:
                # Convert to dict
                msg_dict = {
                    "message_id": msg.message_id,
                    "text": msg.text,
                    "user_name": msg.user_name,
                    "channel_name": msg.channel_name,
                    "timestamp": msg.timestamp,
                    "thread_ts": msg.thread_ts
                }
                
                if memory.index_message(msg_dict):
                    success_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                error_count += 1
                # Continue even if one fails
                continue
                
        console.print(f"\n[green]✅ Backfill Complete![/green]")
        console.print(f"Indexed: {success_count}")
        console.print(f"Errors: {error_count}")
        
    finally:
        db.close()

if __name__ == "__main__":
    # Check if API key exists
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.getenv("PINECONE_API_KEY"):
        console.print("[yellow]⚠️  PINECONE_API_KEY not found in env. Creating dummy run...[/yellow]")
    
    asyncio.run(backfill())

