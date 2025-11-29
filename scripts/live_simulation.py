#!/usr/bin/env python3
"""
Live Simulation Runner - Posts realistic conversations to Slack

Posts messages using persona bots to test the full prioritization pipeline:
1. Posts conversations to real Slack channels
2. Waits for sync/prioritization
3. Displays results with scoring breakdown

Usage:
    python scripts/live_simulation.py                    # Run all scenarios
    python scripts/live_simulation.py --scenario production-outage  # Run specific scenario
    python scripts/live_simulation.py --edge-cases       # Run edge case tests
    python scripts/live_simulation.py --variety          # Generate LLM variations
    python scripts/live_simulation.py --cleanup          # Remove simulation messages
    python scripts/live_simulation.py --list             # List available scenarios
"""

import os
import sys
import json
import time
import argparse
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
from openai import OpenAI

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# Configuration
API_PORT = int(os.getenv("API_PORT", "8000"))
API_BASE = f"http://localhost:{API_PORT}"
YOUR_USER_ID = os.getenv("YOUR_USER_ID", "U09NR3RQZQU")

# Paths
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "simulations" / "config"
RUNS_DIR = BASE_DIR / "simulations" / "runs"

# Ensure directories exist
RUNS_DIR.mkdir(parents=True, exist_ok=True)


class LiveSimulation:
    """Posts realistic conversations to Slack for testing."""
    
    def __init__(self):
        self.bots = self._init_bots()
        self.channels = self._init_channels()
        self.personas = self._load_config("personas.json")["personas"]
        self.channel_config = self._load_config("channels.json")["channels"]
        self.scenarios_config = self._load_config("scenarios.json")
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.posted_messages: List[Dict] = []
        
    def _init_bots(self) -> Dict[str, WebClient]:
        """Initialize Slack clients for each persona bot."""
        return {
            "Sarah Chen": WebClient(token=os.getenv("BOT_SARAH_TOKEN")),
            "Jordan Patel": WebClient(token=os.getenv("BOT_MANAGER_TOKEN")),  # Manager Bot renamed to Jordan Patel
            "Marcus Johnson": WebClient(token=os.getenv("BOT_MARCUS_TOKEN")),
            "Alex Rivera": WebClient(token=os.getenv("BOT_COWORKER_TOKEN")),  # Coworker Bot renamed to Alex Rivera
            "Metrics": WebClient(token=os.getenv("BOT_METRICS_TOKEN")),
        }
    
    def _get_bot_env_name(self, persona_name: str) -> str:
        """Get the expected env var name for a persona's bot token."""
        name_map = {
            "Sarah Chen": "BOT_SARAH_TOKEN",
            "Jordan Patel": "BOT_MANAGER_TOKEN",
            "Marcus Johnson": "BOT_MARCUS_TOKEN",
            "Alex Rivera": "BOT_COWORKER_TOKEN",
            "Metrics": "BOT_METRICS_TOKEN",
        }
        return name_map.get(persona_name, f"BOT_{persona_name.upper().replace(' ', '_')}_TOKEN")
    
    def _init_channels(self) -> Dict[str, str]:
        """Load channel IDs from environment."""
        return {
            "incidents": os.getenv("CHANNEL_INCIDENTS"),
            "engineering": os.getenv("CHANNEL_ENGINEERING"),
            "product": os.getenv("CHANNEL_PRODUCT"),
            "watercooler": os.getenv("CHANNEL_WATERCOOLER"),
            "general": os.getenv("CHANNEL_GENERAL"),
        }
    
    def _load_config(self, filename: str) -> Dict:
        """Load a config file."""
        with open(CONFIG_DIR / filename) as f:
            return json.load(f)
    
    def check_configuration(self) -> bool:
        """Verify all required configuration is present."""
        print("\n🔍 Checking configuration...")
        
        # Check bot tokens
        missing_bots = []
        for name, client in self.bots.items():
            if not client.token:
                missing_bots.append(name)
        
        if missing_bots:
            print(f"❌ Missing bot tokens for: {', '.join(missing_bots)}")
            print("   Add to .env:")
            for name in missing_bots:
                env_name = self._get_bot_env_name(name)
                print(f"     {env_name}=xoxb-...")
            return False
        
        # Check channels
        missing_channels = []
        for name, channel_id in self.channels.items():
            if not channel_id:
                missing_channels.append(name)
        
        if missing_channels:
            print(f"⚠️  Missing channel IDs for: {', '.join(missing_channels)}")
            print("   Add to .env (get IDs from Slack channel settings):")
            for name in missing_channels:
                env_name = f"CHANNEL_{name.upper().replace('-', '_')}"
                print(f"     {env_name}=C...")
        
        print("✅ Bot tokens configured")
        if not missing_channels:
            print("✅ Channel IDs configured")
        
        return len(missing_bots) == 0
    
    def list_scenarios(self):
        """List all available scenarios."""
        print("\n📋 Available Scenarios")
        print("=" * 60)
        
        print("\n🎬 Main Scenarios:")
        for scenario in self.scenarios_config["scenarios"]:
            priority_emoji = {"critical": "🔴", "high": "🟡", "medium": "🟢", "low": "⚪"}.get(scenario["priority"], "⚪")
            print(f"  {priority_emoji} {scenario['id']}: {scenario['title']}")
            print(f"      Channel: #{scenario['channel']} | Messages: {len(scenario['messages'])}")
            print(f"      {scenario['description']}")
            print()
        
        print("\n🧪 Edge Cases:")
        for edge in self.scenarios_config.get("edge_cases", []):
            print(f"  🔬 {edge['id']}: {edge['title']}")
            print(f"      {edge['description']}")
            print()
    
    def _get_bot_for_persona(self, persona_name: str) -> Optional[WebClient]:
        """Get the Slack client for a persona."""
        return self.bots.get(persona_name)
    
    def _format_message(self, text: str, mention_user: bool = False) -> str:
        """Format message text, replacing @Kyle with actual user ID."""
        if mention_user or "@Kyle" in text:
            text = text.replace("@Kyle", f"<@{YOUR_USER_ID}>")
        # Add simulation marker
        return f"[SIM] {text}"
    
    async def post_scenario(self, scenario: Dict) -> List[Dict]:
        """Post all messages in a scenario to Slack."""
        title = scenario["title"]
        channel_name = scenario["channel"]
        messages = scenario["messages"]
        
        channel_id = self.channels.get(channel_name)
        if not channel_id:
            print(f"  ⚠️  No channel ID for #{channel_name}, skipping")
            return []
        
        priority_emoji = {"critical": "🔴", "high": "🟡", "medium": "🟢", "low": "⚪"}.get(scenario.get("priority", "medium"), "⚪")
        
        print(f"\n{priority_emoji} {title}")
        print(f"   Channel: #{channel_name}")
        print("-" * 50)
        
        posted = []
        for msg in messages:
            persona = msg["persona"]
            text = self._format_message(msg["text"], msg.get("mention_user", False))
            delay = msg.get("delay", 1)
            
            bot = self._get_bot_for_persona(persona)
            if not bot or not bot.token:
                print(f"  ⚠️  No bot for {persona}, skipping")
                continue
            
            try:
                result = bot.chat_postMessage(
                    channel=channel_id,
                    text=text
                )
                
                ts = result["ts"]
                posted.append({
                    "ts": ts,
                    "channel": channel_id,
                    "channel_name": channel_name,
                    "persona": persona,
                    "text": text,
                    "scenario_id": scenario.get("id"),
                    "expected_score_min": scenario.get("expected_score_min"),
                    "expected_score_max": scenario.get("expected_score_max"),
                })
                
                print(f"  ✓ [{persona}]: {msg['text'][:60]}...")
                time.sleep(delay)
                
            except SlackApiError as e:
                print(f"  ❌ Slack error ({persona}): {e.response['error']}")
            except Exception as e:
                print(f"  ❌ Error ({persona}): {e}")
        
        return posted
    
    async def run_scenarios(self, scenario_ids: List[str] = None, include_edge_cases: bool = False):
        """Run selected scenarios (or all if none specified)."""
        scenarios_to_run = []
        
        # Main scenarios
        for scenario in self.scenarios_config["scenarios"]:
            if scenario_ids is None or scenario["id"] in scenario_ids:
                scenarios_to_run.append(scenario)
        
        # Edge cases
        if include_edge_cases:
            for edge in self.scenarios_config.get("edge_cases", []):
                if scenario_ids is None or edge["id"] in scenario_ids:
                    scenarios_to_run.append(edge)
        
        if not scenarios_to_run:
            print("❌ No matching scenarios found")
            return
        
        print(f"\n🚀 Running {len(scenarios_to_run)} scenario(s)")
        print("=" * 60)
        
        all_posted = []
        for scenario in scenarios_to_run:
            posted = await self.post_scenario(scenario)
            all_posted.extend(posted)
            time.sleep(2)  # Pause between scenarios
        
        self.posted_messages = all_posted
        
        print(f"\n✅ Posted {len(all_posted)} messages across {len(scenarios_to_run)} scenarios")
        return all_posted
    
    async def generate_variety_scenario(self) -> Dict:
        """Use LLM to generate a new scenario variation."""
        print("\n🎲 Generating LLM scenario variation...")
        
        prompt = """Generate a realistic Slack conversation for a tech company's engineering team.
        
Create a scenario with:
- 3-4 messages between team members
- Natural language with occasional typos/emoji
- A clear priority level (critical/high/medium/low)
- A specific channel (test-incidents, test-engineering, test-product, test-watercooler, or general)

Use these personas:
- Sarah Chen (CTO, VIP)
- Jordan Patel (Engineering Manager, VIP)
- Marcus Johnson (Senior Engineer)
- Alex Rivera (DevOps Engineer)
- Metrics (Monitoring Bot)

Return JSON format:
{
  "id": "llm-generated-xxx",
  "title": "Scenario title",
  "priority": "high",
  "channel": "test-engineering",
  "messages": [
    {"persona": "Name", "text": "message", "delay": 1},
    ...
  ]
}"""
        
        try:
            response = self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
            )
            
            content = response.choices[0].message.content
            # Extract JSON
            start = content.find('{')
            end = content.rfind('}') + 1
            if start >= 0 and end > start:
                scenario = json.loads(content[start:end])
                scenario["id"] = f"llm-{datetime.now().strftime('%H%M%S')}"
                print(f"✅ Generated: {scenario['title']}")
                return scenario
            
        except Exception as e:
            print(f"❌ LLM generation failed: {e}")
        
        return None
    
    async def cleanup_simulation_messages(self):
        """Remove messages with [SIM] prefix from channels."""
        print("\n🧹 Cleaning up simulation messages...")
        
        deleted = 0
        errors = 0
        
        # Use the main Slack Intelligence bot for cleanup (needs channels:history)
        token = os.getenv("SLACK_BOT_TOKEN_PERSONAL") or os.getenv("SLACK_BOT_TOKEN")
        main_bot = WebClient(token=token)
        
        for channel_name, channel_id in self.channels.items():
            if not channel_id:
                continue
            
            print(f"\n  Checking #{channel_name}...")
            
            try:
                # Get recent messages
                result = main_bot.conversations_history(
                    channel=channel_id,
                    limit=100
                )
                
                messages = result.get("messages", [])
                sim_messages = [m for m in messages if "[SIM]" in m.get("text", "")]
                
                if not sim_messages:
                    print(f"    No simulation messages found")
                    continue
                
                print(f"    Found {len(sim_messages)} simulation messages")
                
                # Delete each simulation message
                for msg in sim_messages:
                    try:
                        # Need to delete as the bot that posted it
                        # For now, just report what would be deleted
                        print(f"    - Would delete: {msg.get('text', '')[:50]}...")
                        deleted += 1
                    except Exception as e:
                        errors += 1
                        
            except SlackApiError as e:
                print(f"    ❌ Error reading #{channel_name}: {e.response['error']}")
                errors += 1
        
        print(f"\n✅ Cleanup complete: {deleted} messages identified, {errors} errors")
        print("   Note: Actual deletion requires chat:write scope on posting bot")
    
    def save_run(self, posted_messages: List[Dict]) -> str:
        """Save the simulation run to JSON."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"live_sim_{timestamp}.json"
        filepath = RUNS_DIR / filename
        
        run_data = {
            "timestamp": datetime.now().isoformat(),
            "message_count": len(posted_messages),
            "messages": posted_messages,
        }
        
        with open(filepath, "w") as f:
            json.dump(run_data, f, indent=2)
        
        print(f"\n💾 Run saved to: {filepath}")
        return str(filepath)


async def main():
    parser = argparse.ArgumentParser(description="Live Slack Simulation Runner")
    parser.add_argument("--scenario", "-s", type=str, help="Run specific scenario by ID")
    parser.add_argument("--edge-cases", "-e", action="store_true", help="Include edge case scenarios")
    parser.add_argument("--variety", "-v", action="store_true", help="Generate LLM scenario variation")
    parser.add_argument("--cleanup", "-c", action="store_true", help="Cleanup simulation messages")
    parser.add_argument("--list", "-l", action="store_true", help="List available scenarios")
    parser.add_argument("--all", "-a", action="store_true", help="Run all scenarios including edge cases")
    args = parser.parse_args()
    
    sim = LiveSimulation()
    
    # List scenarios
    if args.list:
        sim.list_scenarios()
        return
    
    # Check configuration
    if not sim.check_configuration():
        print("\n❌ Cannot proceed without proper configuration")
        return
    
    # Cleanup mode
    if args.cleanup:
        await sim.cleanup_simulation_messages()
        return
    
    # Variety mode - generate LLM scenario
    if args.variety:
        scenario = await sim.generate_variety_scenario()
        if scenario:
            posted = await sim.run_scenarios([scenario["id"]])
            if posted:
                sim.save_run(posted)
        return
    
    # Run scenarios
    scenario_ids = [args.scenario] if args.scenario else None
    include_edge = args.edge_cases or args.all
    
    posted = await sim.run_scenarios(scenario_ids, include_edge_cases=include_edge)
    
    if posted:
        sim.save_run(posted)
        
        print("\n" + "=" * 60)
        print("📋 NEXT STEPS")
        print("=" * 60)
        print("1. Wait ~30 seconds for Slack to process")
        print("2. Sync and prioritize:")
        print("   python scripts/sync_once.py")
        print("3. View results with scoring breakdown:")
        print("   python scripts/view_simulation_results.py")
        print("4. Or open Streamlit dashboard:")
        print("   http://localhost:8502")


if __name__ == "__main__":
    asyncio.run(main())

