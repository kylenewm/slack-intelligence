#!/usr/bin/env python3
"""
View Simulation Results with Scoring Breakdown

Shows prioritized messages with clear breakdown of:
- Base score (from LLM content analysis)
- Multipliers applied (VIP, channel)
- Final score

Usage:
    python scripts/view_simulation_results.py              # Show all sim messages
    python scripts/view_simulation_results.py --all        # Show all messages
    python scripts/view_simulation_results.py --hours 1    # Last 1 hour only
"""

import os
import sys
import re
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from backend.database.db import SessionLocal
from backend.database.models import SlackMessage
from backend.database.cache_service import CacheService


def parse_scoring_reason(reason: str) -> Dict[str, Any]:
    """Parse the priority reason to extract base score and multipliers."""
    result = {
        "base_score": None,
        "final_score": None,
        "multipliers": [],
        "original_reason": reason,
    }
    
    if not reason:
        return result
    
    # Look for [Adjusted: ...] pattern
    adjusted_match = re.search(r'\[Adjusted:\s*([^]]+)\]', reason)
    if adjusted_match:
        adjustment_text = adjusted_match.group(1)
        
        # Extract multipliers (e.g., "VIP ×2.0", "priority channel ×1.5")
        multiplier_matches = re.findall(r'([\w\s]+)\s*[×x](\d+\.?\d*)', adjustment_text)
        for name, value in multiplier_matches:
            result["multipliers"].append({
                "name": name.strip(),
                "value": float(value)
            })
        
        # Extract base→final (e.g., "base=85→91")
        score_match = re.search(r'base=(\d+)→(\d+)', adjustment_text)
        if score_match:
            result["base_score"] = int(score_match.group(1))
            result["final_score"] = int(score_match.group(2))
    
    return result


def get_vip_status(user_name: str) -> bool:
    """Check if user is a VIP based on current preferences."""
    cache = CacheService()
    prefs = cache.get_user_preferences("default")
    vip_people = [p.lower().strip() for p in prefs.get("key_people", [])]
    return user_name.lower().strip() in vip_people


def get_channel_type(channel_name: str) -> str:
    """Get channel type (priority/normal/muted) from preferences."""
    cache = CacheService()
    prefs = cache.get_user_preferences("default")
    
    priority_channels = [c.lower().strip() for c in prefs.get("key_channels", [])]
    muted_channels = [c.lower().strip() for c in prefs.get("mute_channels", [])]
    
    channel_lower = channel_name.lower().strip()
    
    if channel_lower in priority_channels:
        return "priority"
    elif channel_lower in muted_channels:
        return "muted"
    return "normal"


def format_message_display(msg: SlackMessage) -> str:
    """Format a single message for display."""
    # Parse scoring info from reason
    scoring = parse_scoring_reason(msg.priority_reason)
    
    # Determine markers
    is_vip = get_vip_status(msg.user_name)
    channel_type = get_channel_type(msg.channel_name)
    is_sim = "[SIM]" in (msg.text or "") or (msg.message_id and msg.message_id.startswith("sim_"))
    
    # Score emoji
    score = msg.priority_score or 0
    if score >= 90:
        score_emoji = "🔴"
    elif score >= 70:
        score_emoji = "🟡"
    elif score >= 50:
        score_emoji = "🟢"
    else:
        score_emoji = "⚪"
    
    # Build markers
    markers = []
    if is_vip:
        markers.append("VIP")
    if channel_type == "priority":
        markers.append("📢 Priority CH")
    elif channel_type == "muted":
        markers.append("🔇 Muted")
    if is_sim:
        markers.append("SIM")
    
    marker_str = f" [{' | '.join(markers)}]" if markers else ""
    
    # Build output
    lines = []
    lines.append(f"{score_emoji} [{score:3d}] {msg.user_name}{marker_str}")
    lines.append(f"       #{msg.channel_name}")
    
    # Show scoring breakdown if available
    if scoring["base_score"] is not None:
        multiplier_str = " → ".join([f"{m['name']} ×{m['value']}" for m in scoring["multipliers"]])
        lines.append(f"       📊 Base: {scoring['base_score']} | {multiplier_str} | Final: {scoring['final_score']}")
    
    # Show message text (truncated)
    text = (msg.text or "")[:80].replace("[SIM] ", "").replace("\n", " ")
    lines.append(f"       \"{text}...\"")
    
    # Show original reason (without adjustment info)
    if msg.priority_reason:
        reason = msg.priority_reason.split("[Adjusted")[0].strip()
        if reason:
            lines.append(f"       💡 {reason[:70]}...")
    
    return "\n".join(lines)


def display_results(messages: List[SlackMessage], show_all: bool = False):
    """Display messages grouped by priority."""
    
    # Group by priority tier
    critical = [m for m in messages if (m.priority_score or 0) >= 90]
    high = [m for m in messages if 70 <= (m.priority_score or 0) < 90]
    medium = [m for m in messages if 50 <= (m.priority_score or 0) < 70]
    low = [m for m in messages if (m.priority_score or 0) < 50]
    
    print("\n" + "=" * 70)
    print("📊 PRIORITIZATION RESULTS WITH SCORING BREAKDOWN")
    print("=" * 70)
    
    # Show current preferences
    cache = CacheService()
    prefs = cache.get_user_preferences("default")
    print(f"\n📋 Current Preferences:")
    print(f"   VIPs: {', '.join(prefs.get('key_people', [])) or 'None'}")
    print(f"   Priority Channels: {', '.join(prefs.get('key_channels', [])) or 'None'}")
    print(f"   Muted Channels: {', '.join(prefs.get('mute_channels', [])) or 'None'}")
    
    # Critical
    if critical:
        print(f"\n🔴 CRITICAL ({len(critical)} messages) - Score 90+")
        print("-" * 70)
        for msg in critical:
            print(format_message_display(msg))
            print()
    
    # High
    if high:
        print(f"\n🟡 HIGH PRIORITY ({len(high)} messages) - Score 70-89")
        print("-" * 70)
        for msg in high:
            print(format_message_display(msg))
            print()
    
    # Medium
    if medium:
        print(f"\n🟢 MEDIUM ({len(medium)} messages) - Score 50-69")
        print("-" * 70)
        for msg in medium:
            print(format_message_display(msg))
            print()
    
    # Low
    if low:
        print(f"\n⚪ LOW ({len(low)} messages) - Score 0-49")
        print("-" * 70)
        for msg in low[:5]:  # Show only first 5 low priority
            print(format_message_display(msg))
            print()
        if len(low) > 5:
            print(f"   ... and {len(low) - 5} more low priority messages")
    
    # Summary
    print("\n" + "=" * 70)
    print("📈 SUMMARY")
    print("=" * 70)
    print(f"   Total: {len(messages)} messages")
    print(f"   🔴 Critical: {len(critical)}")
    print(f"   🟡 High: {len(high)}")
    print(f"   🟢 Medium: {len(medium)}")
    print(f"   ⚪ Low: {len(low)}")
    
    # Check for any scoring anomalies
    print("\n🔍 OBSERVATIONS:")
    
    # VIP in muted channel
    for msg in messages:
        if get_vip_status(msg.user_name) and get_channel_type(msg.channel_name) == "muted":
            score = msg.priority_score or 0
            print(f"   ⚠️  VIP in muted channel: {msg.user_name} in #{msg.channel_name} → score {score}")
    
    # Non-VIP with high score
    high_non_vip = [m for m in critical + high if not get_vip_status(m.user_name)]
    if high_non_vip:
        print(f"   ℹ️  {len(high_non_vip)} high-scoring messages from non-VIPs (urgent content)")


def main():
    parser = argparse.ArgumentParser(description="View Simulation Results")
    parser.add_argument("--all", "-a", action="store_true", help="Show all messages, not just simulation")
    parser.add_argument("--hours", "-t", type=int, default=24, help="Look back N hours (default: 24)")
    parser.add_argument("--limit", "-n", type=int, default=50, help="Max messages to show (default: 50)")
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        # Build query
        cutoff = datetime.now() - timedelta(hours=args.hours)
        
        query = db.query(SlackMessage).filter(
            SlackMessage.timestamp >= cutoff,
            SlackMessage.priority_score.isnot(None)
        )
        
        # Filter to simulation messages unless --all
        if not args.all:
            query = query.filter(
                (SlackMessage.text.contains("[SIM]")) | 
                (SlackMessage.message_id.like("sim_%"))
            )
        
        messages = query.order_by(
            SlackMessage.priority_score.desc()
        ).limit(args.limit).all()
        
        if not messages:
            print("\n❌ No messages found")
            if not args.all:
                print("   Try running with --all to see all messages")
                print("   Or run a simulation first:")
                print("   python scripts/live_simulation.py")
            return
        
        display_results(messages, show_all=args.all)
        
    finally:
        db.close()


if __name__ == "__main__":
    main()

