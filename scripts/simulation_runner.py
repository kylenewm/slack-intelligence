#!/usr/bin/env python3
"""
Simulation Runner for Stress Testing Slack Intelligence

Generates realistic CONVERSATIONAL Slack messages - not random independent messages.
Simulates actual scenarios where people discuss incidents, features, and casual topics.

Usage:
    python scripts/simulation_runner.py                    # Run with 5 messages (quick test)
    python scripts/simulation_runner.py --messages 20      # Run with more messages
    python scripts/simulation_runner.py --replay <file>    # Replay saved run
"""

import os
import sys
import json
import asyncio
import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

import requests
from openai import OpenAI
from dotenv import load_dotenv

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# Configuration
API_PORT = int(os.getenv("API_PORT", "8000"))
API_BASE = f"http://localhost:{API_PORT}"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Paths
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "simulations" / "config"
RUNS_DIR = BASE_DIR / "simulations" / "runs"

# Ensure directories exist
RUNS_DIR.mkdir(parents=True, exist_ok=True)


class ConversationSimulator:
    """Generates realistic conversational Slack scenarios."""
    
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.personas = self._load_config("personas.json")["personas"]
        self.channels = self._load_config("channels.json")["channels"]
        self.generated_messages: List[Dict] = []
        self.results: List[Dict] = []
        
    def _load_config(self, filename: str) -> Dict:
        with open(CONFIG_DIR / filename) as f:
            return json.load(f)
    
    async def generate_scenario(self, scenario_type: str, num_messages: int = 3) -> List[Dict]:
        """Generate a realistic conversation scenario."""
        
        scenarios = {
            "incident": {
                "prompt": """Generate a realistic Slack conversation about a production incident.
The conversation should flow naturally with different people reacting and investigating.

Include:
- Initial alert or report of the issue
- Someone acknowledging and investigating  
- Updates on findings
- Resolution or escalation

Personas available: {personas}
Use #engineering-alerts or #incidents channel.""",
                "channel": "incidents",
            },
            "feature_discussion": {
                "prompt": """Generate a realistic Slack conversation about a feature or technical decision.

Include:
- Someone asking a question or proposing something
- Technical discussion or clarification
- Decision or next steps

Personas available: {personas}
Use #product or #general channel.""",
                "channel": "product",
            },
            "casual": {
                "prompt": """Generate a casual/social Slack conversation.

Include:
- Social chat, coffee runs, weekend plans, etc.
- Keep it light and friendly

Personas available: {personas}
Use #random or #watercooler channel.""",
                "channel": "watercooler",
            }
        }
        
        scenario = scenarios.get(scenario_type, scenarios["incident"])
        persona_names = [p["name"] + f" ({p['role']})" for p in self.personas]
        
        prompt = f"""{scenario['prompt'].format(personas=', '.join(persona_names))}

Generate exactly {num_messages} messages as a natural conversation.
Each message should be under 200 characters.
Format as JSON array:
[
  {{"persona": "Name", "text": "message text", "is_thread_reply": false}},
  {{"persona": "Name", "text": "response", "is_thread_reply": true}},
  ...
]

Make it feel like a real workplace Slack - casual language, occasional typos, emojis where natural."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=800,
            )
            
            content = response.choices[0].message.content
            # Extract JSON from response
            start = content.find('[')
            end = content.rfind(']') + 1
            if start >= 0 and end > start:
                messages_data = json.loads(content[start:end])
            else:
                print(f"  ⚠️ Could not parse LLM response, using fallback")
                return self._fallback_scenario(scenario_type, num_messages)
            
            # Add metadata
            channel = scenario["channel"]
            thread_ts = f"{datetime.now().timestamp():.6f}"
            base_time = datetime.now()
            
            messages = []
            for i, msg in enumerate(messages_data):
                persona = next((p for p in self.personas if p["name"] == msg.get("persona")), self.personas[0])
                
                messages.append({
                    "id": f"sim_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}",
                    "persona": persona["name"],
                    "persona_role": persona["role"],
                    "channel": channel,
                    "text": msg.get("text", "")[:200],
                    "timestamp": (base_time + timedelta(minutes=i*2)).timestamp(),
                    "thread_ts": thread_ts if msg.get("is_thread_reply") else None,
                    "is_reply": msg.get("is_thread_reply", False),
                    "scenario_type": scenario_type,
                    "is_vip": persona.get("is_vip", False),
                    "is_noise": persona.get("is_noise", False),
                })
            
            return messages
            
        except Exception as e:
            print(f"  ❌ Error generating scenario: {e}")
            return self._fallback_scenario(scenario_type, num_messages)
    
    def _fallback_scenario(self, scenario_type: str, num_messages: int) -> List[Dict]:
        """Fallback if LLM generation fails."""
        fallbacks = {
            "incident": [
                {"persona": "AlertBot", "text": "🚨 Alert: High error rate on checkout-api (5xx > 10%)"},
                {"persona": "Marcus", "text": "On it, checking logs now"},
                {"persona": "Lisa", "text": "What's the customer impact? Need to update status page?"},
            ],
            "feature_discussion": [
                {"persona": "Kyle", "text": "Hey team, should we add OAuth support this sprint?"},
                {"persona": "Jordan", "text": "Yes, but let's scope it to Google only for v1"},
            ],
            "casual": [
                {"persona": "Dave", "text": "Anyone want coffee? ☕ Heading to Blue Bottle"},
                {"persona": "Marcus", "text": "I'm in! Large cold brew pls"},
            ]
        }
        
        base_messages = fallbacks.get(scenario_type, fallbacks["incident"])[:num_messages]
        channel = "incidents" if scenario_type == "incident" else "general"
        thread_ts = f"{datetime.now().timestamp():.6f}"
        base_time = datetime.now()
        
        messages = []
        for i, msg in enumerate(base_messages):
            persona = next((p for p in self.personas if p["name"] == msg["persona"]), self.personas[0])
            messages.append({
                "id": f"sim_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}",
                "persona": persona["name"],
                "persona_role": persona.get("role", "Unknown"),
                "channel": channel,
                "text": msg["text"],
                "timestamp": (base_time + timedelta(minutes=i*2)).timestamp(),
                "thread_ts": thread_ts if i > 0 else None,
                "is_reply": i > 0,
                "scenario_type": scenario_type,
                "is_vip": persona.get("is_vip", False),
                "is_noise": persona.get("is_noise", False),
            })
        
        return messages

    async def generate_all_messages(self, total_messages: int = 5) -> List[Dict]:
        """Generate conversational scenarios totaling approximately the target message count."""
        print(f"\n🎲 Generating ~{total_messages} messages across scenarios...")
        
        all_messages = []
        
        # ALWAYS include a mix of scenarios to test prioritization
        if total_messages <= 5:
            # Quick test: 1 incident + 1 casual (test both high and low prio)
            scenarios = [
                ("incident", 3),
                ("casual", 2),
            ]
        elif total_messages <= 15:
            # Medium test: incident + feature + casual
            scenarios = [
                ("incident", total_messages // 3 + 1),
                ("feature_discussion", total_messages // 3),
                ("casual", total_messages // 3),
            ]
        else:
            # Full test: all types
            scenarios = [
                ("incident", total_messages // 3 + 2),
                ("feature_discussion", total_messages // 3),
                ("casual", total_messages // 3),
            ]
        
        for scenario_type, count in scenarios:
            print(f"\n  📝 Generating {scenario_type} scenario ({count} messages)...")
            messages = await self.generate_scenario(scenario_type, count)
            
            for msg in messages:
                print(f"    ✓ [{msg['persona']}] #{msg['channel']}: {msg['text'][:50]}...")
            
            all_messages.extend(messages)
        
        self.generated_messages = all_messages
        print(f"\n✅ Generated {len(all_messages)} messages in {len(scenarios)} scenario(s)")
        return all_messages

    def insert_messages_to_db(self) -> bool:
        """Insert generated messages directly to database."""
        print("\n📥 Inserting messages to database...")
        
        from backend.database.db import SessionLocal
        from backend.database.models import SlackMessage
        
        db = SessionLocal()
        inserted = 0
        
        try:
            for msg in self.generated_messages:
                slack_msg = SlackMessage(
                    message_id=msg["id"],
                    channel_id=f"C_SIM_{msg['channel'].upper().replace('-', '_')}",
                    channel_name=msg["channel"],
                    user_id=f"U_SIM_{msg['persona'].upper()}",
                    user_name=msg["persona"],
                    text=msg["text"],
                    timestamp=datetime.fromtimestamp(msg["timestamp"]),
                    thread_ts=msg.get("thread_ts"),
                    is_thread_parent=not msg.get("is_reply", False),
                )
                db.add(slack_msg)
                inserted += 1
                
            db.commit()
            print(f"✅ Inserted {inserted}/{len(self.generated_messages)} messages")
            return True
            
        except Exception as e:
            print(f"❌ Database error: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    def trigger_prioritization(self) -> bool:
        """Trigger the sync/prioritization endpoint."""
        print("\n🧠 Triggering prioritization...")
        
        try:
            response = requests.post(
                f"{API_BASE}/api/slack/sync",
                params={"hours_ago": 1},
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Prioritized {data.get('prioritization', {}).get('processed', 0)} messages")
                return True
            else:
                print(f"❌ Prioritization failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error during prioritization: {e}")
            return False

    def fetch_results(self) -> List[Dict]:
        """Fetch prioritized results from inbox."""
        print("\n📊 Fetching results...")
        
        try:
            response = requests.get(
                f"{API_BASE}/api/slack/inbox",
                params={"view": "all", "limit": 50},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                messages = data.get("messages", [])
                
                # Filter to only simulation messages
                sim_messages = [m for m in messages if m.get("message_id", "").startswith("sim_")]
                print(f"✅ Retrieved {len(sim_messages)} simulation messages (of {len(messages)} total)")
                return sim_messages
            else:
                print(f"❌ Failed to fetch results: {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ Error fetching results: {e}")
            return []

    def analyze_results(self, results: List[Dict]) -> Dict:
        """Analyze prioritization results."""
        print("\n📈 Analyzing results...")
        
        if not results:
            print("  ⚠️ No results to analyze")
            return {"total": 0}
        
        analysis = {
            "total": len(results),
            "by_score": {
                "critical": [],
                "high": [],
                "medium": [],
                "low": [],
            },
            "by_scenario": {},
        }
        
        for msg in results:
            score = msg.get("priority_score", 0)
            
            if score >= 90:
                analysis["by_score"]["critical"].append(msg)
            elif score >= 70:
                analysis["by_score"]["high"].append(msg)
            elif score >= 50:
                analysis["by_score"]["medium"].append(msg)
            else:
                analysis["by_score"]["low"].append(msg)
        
        # Print summary
        print(f"\n  Score Distribution:")
        print(f"    🔴 Critical (90+): {len(analysis['by_score']['critical'])}")
        for msg in analysis['by_score']['critical']:
            print(f"       [{msg.get('priority_score')}] {msg.get('user_name')}: {msg.get('text', '')[:40]}...")
            
        print(f"    🟠 High (70-89): {len(analysis['by_score']['high'])}")
        for msg in analysis['by_score']['high']:
            print(f"       [{msg.get('priority_score')}] {msg.get('user_name')}: {msg.get('text', '')[:40]}...")
            
        print(f"    🟡 Medium (50-69): {len(analysis['by_score']['medium'])}")
        print(f"    ⚪ Low (<50): {len(analysis['by_score']['low'])}")
        
        return analysis

    def save_run(self, analysis: Dict) -> str:
        """Save the full simulation run to JSON."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{timestamp}.json"
        filepath = RUNS_DIR / filename
        
        run_data = {
            "timestamp": datetime.now().isoformat(),
            "message_count": len(self.generated_messages),
            "messages": self.generated_messages,
            "results": self.results,
            "analysis": {
                "total": analysis.get("total", 0),
                "critical": len(analysis.get("by_score", {}).get("critical", [])),
                "high": len(analysis.get("by_score", {}).get("high", [])),
                "medium": len(analysis.get("by_score", {}).get("medium", [])),
                "low": len(analysis.get("by_score", {}).get("low", [])),
            },
        }
        
        with open(filepath, "w") as f:
            json.dump(run_data, f, indent=2)
        
        print(f"\n💾 Saved run to: {filepath}")
        return str(filepath)

    async def run_simulation(self, num_messages: int = 5):
        """Run full simulation."""
        print("=" * 60)
        print("🚀 CONVERSATION SIMULATION RUNNER")
        print("=" * 60)
        print(f"Mode: Conversational scenarios (~{num_messages} messages)")
        
        # Check server
        try:
            response = requests.get(f"{API_BASE}/health", timeout=5)
            if response.status_code != 200:
                print(f"❌ Server not healthy. Start it first.")
                return
        except:
            print(f"❌ Cannot connect to server at {API_BASE}")
            print(f"   Run: uvicorn backend.main:app --port {API_PORT}")
            return
        
        print("✅ Server is running")
        
        # Generate conversational messages
        await self.generate_all_messages(num_messages)
        
        # Insert to DB
        if not self.insert_messages_to_db():
            print("❌ Failed to insert messages")
            return
        
        # Trigger prioritization
        self.trigger_prioritization()
        
        # Fetch and analyze results
        self.results = self.fetch_results()
        analysis = self.analyze_results(self.results)
        
        # Save run
        run_file = self.save_run(analysis)
        
        print("\n" + "=" * 60)
        print("✅ SIMULATION COMPLETE")
        print("=" * 60)
        print(f"\nGenerated: {len(self.generated_messages)} messages")
        print(f"Results saved to: {run_file}")
        print(f"View in dashboard: http://localhost:8502")

    async def replay_run(self, run_file: str):
        """Replay a saved simulation run."""
        print(f"🔄 Replaying simulation from: {run_file}")
        
        with open(run_file) as f:
            run_data = json.load(f)
        
        self.generated_messages = run_data["messages"]
        print(f"  Loaded {len(self.generated_messages)} messages from saved run")
        
        # Re-insert and re-prioritize
        self.insert_messages_to_db()
        self.trigger_prioritization()
        self.results = self.fetch_results()
        
        analysis = self.analyze_results(self.results)
        
        print("\n✅ Replay complete")
        return analysis


async def main():
    parser = argparse.ArgumentParser(description="Conversation Simulation Runner")
    parser.add_argument("--messages", "-m", type=int, default=5, help="Target number of messages (default: 5)")
    parser.add_argument("--replay", type=str, help="Path to a saved run JSON file to replay")
    args = parser.parse_args()
    
    simulator = ConversationSimulator()
    
    if args.replay:
        await simulator.replay_run(args.replay)
    else:
        await simulator.run_simulation(args.messages)


if __name__ == "__main__":
    asyncio.run(main())
