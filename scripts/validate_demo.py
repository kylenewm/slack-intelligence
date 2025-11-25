#!/usr/bin/env python3
"""
Demo Validation Script
Validates that the demo ran successfully and checks for common issues.

Usage:
    python scripts/validate_demo.py
"""

import sys
from pathlib import Path
from typing import List, Dict, Any

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database.cache_service import CacheService
from backend.config import settings

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
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
        print(f"✅ {title}")
        print("="*70 + "\n")


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


def validate_messages() -> Dict[str, Any]:
    """Validate that messages exist and are prioritized"""
    cache = CacheService()
    
    # Get all messages (using score range instead of category 'all')
    all_messages = cache.get_messages_by_score_range(
        min_score=0,
        max_score=100,
        hours_ago=24,
        limit=1000
    )
    
    if not all_messages:
        return {
            'valid': False,
            'error': 'No messages found in database'
        }
    
    # Check prioritization
    prioritized = [m for m in all_messages if m.get('priority_score') is not None]
    unprioritized = [m for m in all_messages if m.get('priority_score') is None]
    
    # Get by category
    critical = cache.get_messages_by_category('needs_response', hours_ago=24, limit=100)
    high = cache.get_messages_by_category('high_priority', hours_ago=24, limit=100)
    medium = cache.get_messages_by_category('fyi', hours_ago=24, limit=100)
    low = cache.get_messages_by_category('low_priority', hours_ago=24, limit=100)
    
    # Validate prioritization makes sense
    issues = []
    
    # Check if @mentions are prioritized high
    your_user_id = settings.KEY_PEOPLE[0] if settings.KEY_PEOPLE else None
    if your_user_id:
        mentions = [m for m in all_messages if f"<@{your_user_id}>" in m.get('text', '')]
        low_mention_scores = [m for m in mentions if m.get('priority_score', 0) < 80]
        if low_mention_scores:
            issues.append(f"{len(low_mention_scores)} @mentions have low priority scores")
    
    # Check if urgent keywords are prioritized
    urgent_keywords = ['urgent', 'asap', 'blocking', 'critical', 'escalation']
    urgent_messages = [
        m for m in all_messages 
        if any(kw in m.get('text', '').lower() for kw in urgent_keywords)
    ]
    low_urgent_scores = [m for m in urgent_messages if m.get('priority_score', 0) < 70]
    if low_urgent_scores:
        issues.append(f"{len(low_urgent_scores)} urgent messages have low priority scores")
    
    # Check if casual messages are deprioritized
    casual_keywords = ['happy', 'friday', 'coffee', 'lol', 'casual']
    casual_messages = [
        m for m in all_messages 
        if any(kw in m.get('text', '').lower() for kw in casual_keywords)
    ]
    high_casual_scores = [m for m in casual_messages if m.get('priority_score', 0) >= 70]
    if high_casual_scores:
        issues.append(f"{len(high_casual_scores)} casual messages have high priority scores")
    
    return {
        'valid': len(unprioritized) == 0,
        'total_messages': len(all_messages),
        'prioritized': len(prioritized),
        'unprioritized': len(unprioritized),
        'critical': len(critical),
        'high': len(high),
        'medium': len(medium),
        'low': len(low),
        'issues': issues
    }


def validate_config() -> List[str]:
    """Validate configuration"""
    issues = []
    
    if not settings.SLACK_BOT_TOKEN:
        issues.append("SLACK_BOT_TOKEN not set")
    
    if not settings.OPENAI_API_KEY:
        issues.append("OPENAI_API_KEY not set")
    
    if settings.NOTION_SYNC_ENABLED and not settings.NOTION_API_KEY:
        issues.append("NOTION_SYNC_ENABLED=true but NOTION_API_KEY not set")
    
    return issues


def validate_api() -> Dict[str, bool]:
    """Validate API endpoints (if server is running)"""
    import os
    import requests
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Get API port from environment (default 8000)
    api_port = int(os.getenv("API_PORT", "8000"))
    api_base = f"http://localhost:{api_port}"
    
    try:
        response = requests.get(f"{api_base}/health", timeout=2)
        server_running = response.status_code == 200
    except:
        server_running = False
    
    api_results = {
        'server_running': server_running
    }
    
    if server_running:
        try:
            response = requests.get(f"{api_base}/api/slack/inbox?view=all&limit=10", timeout=2)
            api_results['inbox_endpoint'] = response.status_code == 200
        except:
            api_results['inbox_endpoint'] = False
    
    return api_results


def main():
    """Main validation function"""
    print_header("Demo Validation")
    
    all_valid = True
    
    # Validate configuration
    print("Checking configuration...")
    config_issues = validate_config()
    if config_issues:
        all_valid = False
        for issue in config_issues:
            print_error(issue)
    else:
        print_success("Configuration valid")
    
    # Validate messages
    print("\nValidating messages and prioritization...")
    msg_result = validate_messages()
    
    if not msg_result['valid']:
        all_valid = False
        if 'error' in msg_result:
            print_error(msg_result['error'])
        else:
            print_error(f"{msg_result['unprioritized']} messages not prioritized")
    else:
        print_success(f"All {msg_result['total_messages']} messages prioritized")
    
    # Show statistics
    if console:
        stats_table = Table(title="Message Statistics", box=box.ROUNDED)
        stats_table.add_column("Category", style="bold")
        stats_table.add_column("Count", justify="right")
        
        stats_table.add_row("Total Messages", str(msg_result['total_messages']))
        stats_table.add_row("Prioritized", str(msg_result['prioritized']))
        stats_table.add_row("🔴 Needs Response", str(msg_result['critical']))
        stats_table.add_row("🟡 High Priority", str(msg_result['high']))
        stats_table.add_row("🟢 FYI", str(msg_result['medium']))
        stats_table.add_row("⚪ Low Priority", str(msg_result['low']))
        
        console.print(stats_table)
    else:
        print(f"\nMessage Statistics:")
        print(f"  Total: {msg_result['total_messages']}")
        print(f"  Prioritized: {msg_result['prioritized']}")
        print(f"  🔴 Needs Response: {msg_result['critical']}")
        print(f"  🟡 High Priority: {msg_result['high']}")
        print(f"  🟢 FYI: {msg_result['medium']}")
        print(f"  ⚪ Low Priority: {msg_result['low']}")
    
    # Check for issues
    if msg_result.get('issues'):
        print("\n⚠️  Potential Issues:")
        for issue in msg_result['issues']:
            print_warning(issue)
    
    # Validate API (optional)
    print("\nChecking API (optional)...")
    api_results = validate_api()
    if api_results['server_running']:
        print_success("API server is running")
        if api_results.get('inbox_endpoint'):
            print_success("Inbox endpoint accessible")
        else:
            print_warning("Inbox endpoint not accessible")
    else:
        print_warning("API server not running (this is OK for demo validation)")
    
    # Final result
    print("\n" + "="*70)
    if all_valid and not msg_result.get('issues'):
        print_success("✅ Demo validation PASSED")
        print("All checks passed! Demo is ready.")
    else:
        print_error("⚠️  Demo validation has warnings")
        print("Review the issues above, but demo may still work.")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

