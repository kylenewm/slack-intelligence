#!/usr/bin/env python3
"""
Unified Demo Script for Slack Intelligence
The ONE demo entry point - consolidates all demo features.

Usage:
    python scripts/demo.py                    # Quick demo (5 messages, simulation only)
    python scripts/demo.py --full             # Full demo (12 messages, Notion)
    python scripts/demo.py --slack            # Post to real Slack channel
    python scripts/demo.py --ai-generated    # Use AI to generate messages
    python scripts/demo.py --help             # Show all options
"""

import sys
import asyncio
import argparse
import logging
import json
import time
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from openai import OpenAI
from slack_sdk import WebClient
from dotenv import load_dotenv

# Rich for beautiful terminal output
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.table import Table
    from rich import box
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  Install 'rich' for better output: pip install rich")

# Load environment
load_dotenv()

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database.db import init_db
from backend.ai.prioritizer import MessagePrioritizer
from backend.database.cache_service import CacheService
from backend.integrations.notion_service import NotionSyncService
from backend.services.sync_service import SyncService
from backend.config import settings

# Setup logging
logging.basicConfig(
    level=logging.WARNING,  # Suppress verbose logs during demo
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize console if rich is available
console = Console() if RICH_AVAILABLE else None

# Hardcoded demo messages (fallback when not using AI generation)
DEMO_MESSAGES = [
    {
        'message_id': f'demo_{i}',
        'channel_id': 'C123DEMO',
        'channel_name': 'product-strategy',
        'user_id': 'U123',
        'user_name': user,
        'text': text,
        'timestamp': datetime.utcnow(),
        'thread_ts': None,
        'is_thread_parent': False,
        'reply_count': 0,
        'reactions': [],
        'mentioned_users': [],
        'has_files': False
    }
    for i, (user, text) in enumerate([
        ('Sarah Chen (Manager)', '@you URGENT: Production API latency spiked to 5 seconds. Customers complaining. Need immediate plan.'),
        ('Engineering Lead', '@you The intent detection model is showing 15% accuracy drop. Can you prioritize investigation?'),
        ('Sales VP', 'Latest customer feedback: "The chatbot doesn\'t understand complex questions." Need product roadmap update.'),
        ('Data Scientist', 'A/B test results are in: New response model improved conversation quality by 23%. Ready to discuss rollout?'),
        ('Customer Success', 'Escalation: Enterprise client threatening to churn due to response quality issues. Need PM input ASAP.'),
        ('Engineer', 'PR ready for review: Latency optimization changes. Reduces response time by 40%.'),
        ('Product Designer', 'Updated wireframes for the new conversation flow. Would love your feedback when you have time.'),
        ('Weekly Bot', '📊 Weekly Metrics Report\nConversations: 10,234\nSatisfaction: 4.2/5\nIntent Accuracy: 87%'),
        ('Team Lead', 'Reminder: Sprint planning tomorrow at 10am. Please review the backlog.'),
        ('Office Manager', 'Happy Friday team! 🎉 Don\'t forget about the team lunch today at noon.'),
        ('Metrics Bot', '[Automated] Daily dashboard updated. No action required.'),
        ('Random Colleague', 'Anyone want to grab coffee? ☕'),
    ])
]


def print_header(title: str, subtitle: str = ""):
    """Print a formatted header"""
    if console:
        console.print(Panel(
            f"[bold cyan]{title}[/bold cyan]\n{subtitle}" if subtitle else title,
            border_style="cyan",
            box=box.ROUNDED
        ))
    else:
        print("\n" + "="*70)
        print(f"🎬 {title}")
        if subtitle:
            print(subtitle)
        print("="*70 + "\n")


def print_step(step_num: int, title: str):
    """Print a step header"""
    if console:
        console.print(f"\n[bold yellow]Step {step_num}:[/bold yellow] [bold]{title}[/bold]")
        console.print("-" * 70)
    else:
        print(f"\n📦 Step {step_num}: {title}")
        print("-" * 70)


def print_success(message: str):
    """Print success message"""
    if console:
        console.print(f"[green]✅[/green] {message}")
    else:
        print(f"✅ {message}")


def print_error(message: str):
    """Print error message"""
    if console:
        console.print(f"[red]❌[/red] {message}")
    else:
        print(f"❌ {message}")


def print_warning(message: str):
    """Print warning message"""
    if console:
        console.print(f"[yellow]⚠️[/yellow]  {message}")
    else:
        print(f"⚠️  {message}")


async def generate_ai_messages(count: int = 12) -> Optional[List[Dict[str, Any]]]:
    """Generate realistic messages using OpenAI"""
    if not settings.OPENAI_API_KEY:
        print_error("OPENAI_API_KEY not set - cannot generate AI messages")
        return None
    
    print_success(f"Generating {count} realistic messages with AI...")
    
    openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    prompt = f"""Generate {count} realistic Slack messages that an AI Product Manager would receive.
    
You're an AI PM building a conversational virtual sales assistant. Generate a mix of:
- 3 CRITICAL messages (urgent, need immediate response, @mentions, production issues)
- 3 HIGH PRIORITY (important updates, decisions needed, customer feedback)
- 3 MEDIUM (FYI updates, meeting reminders, status updates)
- 3 LOW PRIORITY (casual chat, automated reports, social messages)

Make them realistic and varied. Include specific product context.

Return as JSON array with format:
[{{"text": "message text", "sender_name": "sender name"}}]

Make each message unique and realistic for an AI PM role."""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are helping create realistic Slack message simulations for an AI PM demo."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=2000
        )
        
        content = response.choices[0].message.content
        # Extract JSON from markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        messages = json.loads(content.strip())
        
        # Convert to our format
        formatted_messages = []
        for i, msg in enumerate(messages):
            formatted_messages.append({
                'message_id': f'ai_demo_{i}',
                'channel_id': 'C123DEMO',
                'channel_name': 'product-strategy',
                'user_id': f'U{i}',
                'user_name': msg.get('sender_name', f'User {i}'),
                'text': msg.get('text', ''),
                'timestamp': datetime.utcnow(),
                'thread_ts': None,
                'is_thread_parent': False,
                'reply_count': 0,
                'reactions': [],
                'mentioned_users': [],
                'has_files': False
            })
        
        return formatted_messages
        
    except Exception as e:
        print_error(f"Error generating messages: {e}")
        return None


async def post_to_slack(messages: List[Dict[str, Any]], channel_id: str, mode: str = 'personal') -> List[Any]:
    """Post messages to Slack channel"""
    print_success(f"Posting {len(messages)} messages to Slack...")
    
    # Choose the right bot based on mode
    if mode == 'personal':
        # Use simulation bot for personal Slack (has chat:write)
        slack_token = os.getenv("BOT_COWORKER_TOKEN")
        if not slack_token:
            print_error("BOT_COWORKER_TOKEN not set - cannot post to Slack")
            return []
        slack_client = WebClient(token=slack_token)
    else:
        # Use production bot for work Slack
        slack_client = WebClient(token=settings.SLACK_BOT_TOKEN)
    
    posted = []
    
    if console:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Posting messages...", total=len(messages))
            for msg in messages:
                try:
                    result = slack_client.chat_postMessage(
                        channel=channel_id,
                        text=msg['text'],
                        username=msg.get('user_name', 'Demo User'),
                        icon_emoji=":robot_face:"
                    )
                    posted.append(result)
                    progress.update(task, advance=1)
                    time.sleep(0.5)  # Rate limiting
                except Exception as e:
                    print_error(f"Error posting message: {e}")
                    progress.update(task, advance=1)
    else:
        for i, msg in enumerate(messages):
            try:
                result = slack_client.chat_postMessage(
                    channel=channel_id,
                    text=msg['text'],
                    username=msg.get('user_name', 'Demo User'),
                    icon_emoji=":robot_face:"
                )
                posted.append(result)
                print(f"  ✅ Posted: {msg['text'][:50]}...")
                time.sleep(0.5)
            except Exception as e:
                print_error(f"Error posting message: {e}")
    
    return posted


def display_results(cache: CacheService, notion_result: Optional[Dict] = None):
    """Display prioritization results in a beautiful format"""
    print_step(4, "Prioritization Results")
    
    # Get messages by category
    critical = cache.get_messages_by_category('needs_response', hours_ago=24, limit=10)
    high = cache.get_messages_by_category('high_priority', hours_ago=24, limit=10)
    medium = cache.get_messages_by_category('fyi', hours_ago=24, limit=10)
    low = cache.get_messages_by_category('low_priority', hours_ago=24, limit=10)
    
    total = len(critical) + len(high) + len(medium) + len(low)
    
    if console:
        # Create summary table
        summary_table = Table(title="Message Prioritization Summary", box=box.ROUNDED)
        summary_table.add_column("Category", style="bold")
        summary_table.add_column("Count", justify="right")
        summary_table.add_column("Percentage", justify="right")
        
        summary_table.add_row("🔴 Needs Response", str(len(critical)), f"{len(critical)/total*100:.1f}%")
        summary_table.add_row("🟡 High Priority", str(len(high)), f"{len(high)/total*100:.1f}%")
        summary_table.add_row("🟢 FYI", str(len(medium)), f"{len(medium)/total*100:.1f}%")
        summary_table.add_row("⚪ Low Priority", str(len(low)), f"{len(low)/total*100:.1f}%")
        summary_table.add_row("", "", "")
        summary_table.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]", "100%")
        
        console.print(summary_table)
        
        # Show top messages
        if critical:
            console.print("\n[bold red]🔴 NEEDS RESPONSE[/bold red]")
            for msg in critical[:3]:
                console.print(f"  [{msg['priority_score']}] {msg['user_name']}")
                console.print(f"  {msg['text'][:70]}...")
                console.print(f"  → {msg['priority_reason']}\n")
        
        if high:
            console.print("[bold yellow]🟡 HIGH PRIORITY[/bold yellow]")
            for msg in high[:2]:
                console.print(f"  [{msg['priority_score']}] {msg['user_name']}: {msg['text'][:60]}...")
        
        if notion_result:
            console.print(f"\n[bold cyan]📝 Notion Sync:[/bold cyan] {notion_result['tasks_created']} tasks created")
    else:
        print(f"🔴 NEEDS RESPONSE ({len(critical)} messages)")
        for msg in critical[:3]:
            print(f"   [{msg['priority_score']}] {msg['user_name']}")
            print(f"   {msg['text'][:70]}...")
            print(f"   → {msg['priority_reason']}\n")
        
        print(f"🟡 HIGH PRIORITY ({len(high)} messages)")
        for msg in high[:2]:
            print(f"   [{msg['priority_score']}] {msg['user_name']}: {msg['text'][:60]}...")
        
        if notion_result:
            print(f"\n📝 Notion Sync: {notion_result['tasks_created']} tasks created")


def display_metrics(total_messages: int, needs_response: int, duration: float):
    """Display demo metrics and ROI"""
    print_step(5, "Demo Metrics & ROI")
    
    # Calculate metrics
    time_saved_per_message = 0.05  # 3 seconds per message (500 messages = 25 min)
    total_time_saved = total_messages * time_saved_per_message
    cost_per_message = 0.001  # ~$0.50/day for 500 messages
    total_cost = total_messages * cost_per_message
    
    if console:
        metrics_table = Table(title="Value Proposition", box=box.ROUNDED)
        metrics_table.add_column("Metric", style="bold")
        metrics_table.add_column("Value", justify="right")
        
        metrics_table.add_row("Messages Processed", str(total_messages))
        metrics_table.add_row("Critical Messages", f"[red]{needs_response}[/red]")
        metrics_table.add_row("Time Saved", f"{total_time_saved:.1f} minutes")
        metrics_table.add_row("Cost", f"${total_cost:.3f}")
        metrics_table.add_row("Demo Duration", f"{duration:.1f} seconds")
        metrics_table.add_row("", "")
        metrics_table.add_row("[bold]Before:[/bold]", f"Scan {total_messages} messages (~{total_messages * 0.05:.1f} min)")
        metrics_table.add_row("[bold]After:[/bold]", f"Review {needs_response} critical messages (~{needs_response * 0.05:.1f} min)")
        
        console.print(metrics_table)
    else:
        print(f"Messages Processed: {total_messages}")
        print(f"Critical Messages: {needs_response}")
        print(f"Time Saved: {total_time_saved:.1f} minutes")
        print(f"Cost: ${total_cost:.3f}")
        print(f"\nBefore: Scan {total_messages} messages (~{total_messages * 0.05:.1f} min)")
        print(f"After: Review {needs_response} critical messages (~{needs_response * 0.05:.1f} min)")


async def run_demo(
    mode: str = 'quick',
    ai_generated: bool = False,
    channel_id: str = None,
    verbose: bool = False
):
    """Run the unified demo - Full end-to-end workflow
    
    Args:
        mode: 'quick' (5 messages) or 'full' (12 messages)
        ai_generated: Use AI to generate messages instead of hardcoded ones
        channel_id: Slack channel ID (REQUIRED)
        verbose: Show verbose logging
    
    Note: Slack and Notion are REQUIRED for this demo.
    """
    
    start_time = time.time()
    
    # Determine message count based on mode
    message_count = 5 if mode == 'quick' else 12
    
    # Print header
    print_header(
        "Slack Intelligence - Full End-to-End Demo",
        f"Mode: {mode.upper()} | Messages: {message_count} | Slack: Yes | Notion: Yes"
    )
    
    # Step 1: Initialize Database
    print_step(1, "Initialize Database")
    init_db()
    print_success("Database initialized")
    
    # Step 2: Generate/Get Messages
    print_step(2, "Prepare Messages")
    if ai_generated:
        messages = await generate_ai_messages(message_count)
        if not messages:
            print_warning("AI generation failed, using hardcoded messages")
            messages = DEMO_MESSAGES[:message_count]
    else:
        messages = DEMO_MESSAGES[:message_count]
        print_success(f"Using {len(messages)} demo messages")
    
    # Step 2b: Post to Slack (always required)
    if not channel_id:
        print_error("Channel ID is required")
        print("Usage: python scripts/demo.py --channel C123ABC")
        return
    
    slack_mode = 'personal'  # Default to personal Slack
    posted = await post_to_slack(messages, channel_id, slack_mode)
    if not posted:
        print_error("Failed to post messages to Slack. Cannot continue.")
        return
    
    print_success(f"Posted {len(posted)} messages to Slack")
    print("⏳ Waiting 5 seconds for Slack to index messages...")
    await asyncio.sleep(5)  # Increased wait time for Slack indexing
    
    # Step 3: Fetch messages back from Slack and save to database
    print_step(3, "Fetch Messages from Slack")
    
    # Temporarily override token for personal Slack BEFORE creating service
    original_token = settings.SLACK_BOT_TOKEN
    if slack_mode == 'personal':
        personal_token = os.getenv("SLACK_BOT_TOKEN_PERSONAL")
        if personal_token:
            settings.SLACK_BOT_TOKEN = personal_token
    
    # Create sync service with the correct token
    sync_service = SyncService()
    
    # Sync will fetch and save the messages
    result = await sync_service.sync(channel_ids=[channel_id], hours_ago=1)
    settings.SLACK_BOT_TOKEN = original_token
    
    fetched_count = result.get('fetch', {}).get('new_messages', 0)
    print_success(f"Fetched and saved {fetched_count} new messages from Slack")
    
    # Step 4: AI Prioritization
    print_step(4, "AI Prioritization")
    print("Analyzing messages with OpenAI GPT-4o-mini...")
    
    prioritizer = MessagePrioritizer()
    
    if console:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Prioritizing messages...", total=None)
            priority_result = await prioritizer.prioritize_new_messages()
            progress.update(task, completed=True)
    else:
        priority_result = await prioritizer.prioritize_new_messages()
    
    print_success(f"Prioritized {priority_result['prioritized']} messages")
    
    # Step 5: Notion Sync (always required)
    if not settings.NOTION_SYNC_ENABLED:
        print_error("Notion sync is disabled but required for this demo")
        print("Please set NOTION_SYNC_ENABLED=true in .env")
        print("Also ensure NOTION_API_KEY and NOTION_DATABASE_ID are set")
        return
    
    if not settings.NOTION_API_KEY or not settings.NOTION_DATABASE_ID:
        print_error("Notion credentials missing")
        print("Please set NOTION_API_KEY and NOTION_DATABASE_ID in .env")
        return
    
    print_step(5, "Sync to Notion")
    cache = CacheService()
    high_priority_msgs = cache.get_messages_by_score_range(
        min_score=settings.NOTION_MIN_PRIORITY_SCORE,
        hours_ago=24,
        limit=100
    )
    
    notion = NotionSyncService(
        api_key=settings.NOTION_API_KEY,
        database_id=settings.NOTION_DATABASE_ID
    )
    
    notion_result = await notion.sync_messages_to_notion(high_priority_msgs)
    
    print_success(f"Notion Sync Complete: {notion_result['tasks_created']} tasks created")
    
    # Display Results
    display_results(cache, notion_result)
    
    # Display Metrics
    critical_count = len(cache.get_messages_by_category('needs_response', hours_ago=24, limit=100))
    duration = time.time() - start_time
    display_metrics(fetched_count, critical_count, duration)
    
    # Final Summary
    print_header("Demo Complete!", "")
    
    if console:
        console.print("[bold green]✅ What This Demonstrated:[/bold green]")
        console.print("  1. Posted messages to Slack and fetched them back")
        console.print("  2. AI-powered prioritization with GPT-4o-mini")
        console.print("  3. Smart categorization into 4 priority levels")
        if notion_result:
            console.print(f"  4. Created {notion_result['tasks_created']} tasks in Notion")
        console.print("\n[bold cyan]💡 Interview Talking Points:[/bold cyan]")
        console.print("  - End-to-end AI-powered workflow")
        console.print("  - OpenAI integration for intelligent prioritization")
        console.print("  - External API integration (Notion)")
        console.print("  - Production-ready architecture")
        console.print("  - Real-world problem solving (Slack overload)")
    else:
        print("✅ What This Demonstrated:")
        print("  1. Posted messages to Slack and fetched them back")
        print("  2. AI-powered prioritization with GPT-4o-mini")
        print("  3. Smart categorization into 4 priority levels")
        if notion_result:
            print(f"  4. Created {notion_result['tasks_created']} tasks in Notion")
        print("\n💡 Interview Talking Points:")
        print("  - End-to-end AI-powered workflow")
        print("  - OpenAI integration for intelligent prioritization")
        print("  - External API integration (Notion)")
        print("  - Production-ready architecture")
        print("  - Real-world problem solving (Slack overload)")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Unified Demo Script for Slack Intelligence - Full End-to-End Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/demo.py --channel C123ABC                    # Quick demo (5 messages)
  python scripts/demo.py --full --channel C123ABC              # Full demo (12 messages)
  python scripts/demo.py --channel C123ABC --ai-generated     # Use AI to generate messages
  python scripts/demo.py --full --channel C123ABC --ai-generated  # Complete demo with AI

Note: Slack and Notion are REQUIRED for this demo. Make sure:
  - Your bots are invited to the channel
  - NOTION_SYNC_ENABLED=true in .env
  - NOTION_API_KEY and NOTION_DATABASE_ID are set
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['quick', 'full'],
        default='quick',
        help='Demo mode: quick (5 messages) or full (12 messages)'
    )
    
    parser.add_argument(
        '--channel',
        type=str,
        required=True,
        help='Slack channel ID (REQUIRED)'
    )
    
    parser.add_argument(
        '--ai-generated',
        action='store_true',
        help='Use AI to generate realistic messages instead of hardcoded ones'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show verbose logging'
    )
    
    args = parser.parse_args()
    
    # Validate channel ID format
    if not args.channel.startswith('C'):
        parser.error("Channel ID must start with 'C' (e.g., C123ABC)")
    
    # Map mode argument
    mode = args.mode
    
    # Run demo (Slack and Notion are always enabled)
    try:
        asyncio.run(run_demo(
            mode=mode,
            ai_generated=args.ai_generated,
            channel_id=args.channel,
            verbose=args.verbose
        ))
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Demo failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

