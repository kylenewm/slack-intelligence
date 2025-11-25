#!/usr/bin/env python3
"""
Comprehensive simulation runner for AI PM role.
Generates realistic messages, syncs, and validates prioritization.
"""

import os
import asyncio
import subprocess
import time
import requests
from dotenv import load_dotenv
from llm_simulation_generator import LLMSimulationGenerator

# Load environment variables
load_dotenv()

# Get API port from environment (default 8000)
API_PORT = int(os.getenv("API_PORT", "8000"))
API_BASE = f"http://localhost:{API_PORT}"

def check_server():
    """Check if the server is running"""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def sync_messages():
    """Sync messages from Slack"""
    print("🔄 Syncing messages...")
    try:
        response = requests.post(f"{API_BASE}/api/slack/sync?hours_ago=1")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Synced {data['fetch']['new_messages']} new messages")
            return True
        else:
            print(f"❌ Sync failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Sync error: {e}")
        return False

def validate_results():
    """Run the validation script"""
    print("🔍 Validating prioritization...")
    try:
        result = subprocess.run([
            "python", "scripts/validate_prioritization.py"
        ], capture_output=True, text=True, cwd=".")
        
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
            
    except Exception as e:
        print(f"❌ Validation error: {e}")

async def run_simulation_cycle(channel_id, messages_per_category=8):
    """Run one complete simulation cycle"""
    
    print("🚀 Starting Comprehensive Simulation")
    print("=" * 60)
    print(f"📤 Channel: {channel_id}")
    print(f"📊 Messages per category: {messages_per_category}")
    print()
    
    # Step 1: Generate and post messages
    print("Step 1: Generating realistic messages...")
    generator = LLMSimulationGenerator()
    await generator.run_simulation(channel_id, messages_per_category)
    
    print("\n" + "="*60)
    print("Step 2: Syncing and prioritizing messages...")
    
    # Step 2: Sync messages
    if not sync_messages():
        print("❌ Failed to sync messages")
        return False
    
    print("\n" + "="*60)
    print("Step 3: Validating prioritization accuracy...")
    
    # Step 3: Validate results
    validate_results()
    
    print("\n" + "="*60)
    print("🎉 Simulation cycle complete!")
    print()
    print("Next steps:")
    print("- Review the prioritization results above")
    print("- Adjust KEY_PEOPLE, KEY_CHANNELS, KEY_KEYWORDS if needed")
    print("- Run another cycle to test improvements")
    print("- When satisfied, transfer to production Slack")
    
    return True

async def main():
    """Main simulation runner"""
    
    print("🤖 AI PM Comprehensive Simulation")
    print("=" * 50)
    print("This will generate realistic messages for your AI PM role")
    print("building a conversational virtual sales assistant.")
    print()
    
    # Check server
    if not check_server():
        print("❌ Server not running. Please start it first:")
        print("   source venv/bin/activate")
        print(f"   uvicorn backend.main:app --host 0.0.0.0 --port {API_PORT}")
        return
    
    print("✅ Server is running")
    print()
    
    # Get channel ID
    channel_id = input("Enter channel ID to post messages to: ").strip()
    
    if not channel_id:
        print("❌ Channel ID required")
        return
    
    if not channel_id.startswith('C'):
        print("❌ Channel ID should start with 'C'")
        return
    
    # Get message count
    try:
        messages_per_category = int(input("Messages per category (default 8): ") or "8")
    except ValueError:
        messages_per_category = 8
    
    # Run simulation
    success = await run_simulation_cycle(channel_id, messages_per_category)
    
    if success:
        print("\n🎯 Simulation completed successfully!")
        print("Check the results above to see how well the prioritization worked.")
    else:
        print("\n❌ Simulation failed. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())
