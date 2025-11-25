#!/usr/bin/env python3
"""
LLM-powered simulation generator for AI PM building conversational virtual sales assistant.
Generates realistic messages and validates prioritization accuracy.
"""

import os
import time
import asyncio
import json
from datetime import datetime
from slack_sdk import WebClient
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize clients
bots = {
    "manager": WebClient(token=os.getenv("BOT_MANAGER_TOKEN")),
    "coworker": WebClient(token=os.getenv("BOT_COWORKER_TOKEN")),
    "metrics": WebClient(token=os.getenv("BOT_METRICS_TOKEN")),
}

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Your user ID
YOUR_USER_ID = os.getenv("YOUR_USER_ID", "U09NR3RQZQU")

# Simulation context for your role
SIMULATION_CONTEXT = """
You are an AI Product Manager building a conversational virtual sales assistant. 
Your team includes:
- Engineering team working on intent detection, response generation, and latency optimization
- Data scientists running A/B tests on conversation quality
- Sales team providing customer feedback and requirements
- Customer support handling escalations
- Stakeholders from business operations and leadership

Key projects:
- Intent detection accuracy improvements
- Response quality optimization  
- Latency reduction for real-time conversations
- A/B testing conversation flows
- Customer feedback integration
- Sales performance metrics

Channels you work in:
- #product-strategy - Strategic discussions and roadmap
- #project-intent-detection - Active work on intent classification
- #project-response-quality - Response generation improvements
- #stakeholder-feedback - Customer and sales team input
- #experiment-results - A/B test results and metrics
- #weekly-updates - Team status reports
"""

class LLMSimulationGenerator:
    def __init__(self):
        self.openai = openai_client
        self.bots = bots
        self.your_user_id = YOUR_USER_ID
        
    async def generate_messages_for_category(self, category, count=10):
        """Generate realistic messages for a specific priority category"""
        
        category_prompts = {
            "critical": f"""
Generate {count} realistic Slack messages that an AI PM would receive that are CRITICAL and need immediate response.
These should be direct questions, urgent decisions, or blocking issues related to building a conversational virtual sales assistant.

Examples of critical messages:
- Direct @mentions asking for decisions on product features
- Urgent customer escalations requiring PM input
- Production issues blocking sales conversations
- Deadline-driven requests for approvals
- Stakeholder escalations

Make them realistic for an AI PM role. Include @mentions to the user, urgent keywords, and specific product context.
Format as JSON array of message objects with 'text' and 'sender_role' fields.
""",
            
            "high_priority": f"""
Generate {count} realistic Slack messages that are HIGH PRIORITY for an AI PM building a conversational sales assistant.
These should be important but not requiring immediate response.

Examples:
- Production alerts and system issues
- Customer feedback requiring attention
- Experiment results showing significant changes
- Important updates from stakeholders
- Technical discussions about product decisions

Make them realistic and specific to the AI PM role. Include relevant keywords and context.
Format as JSON array of message objects with 'text' and 'sender_role' fields.
""",
            
            "medium_priority": f"""
Generate {count} realistic Slack messages that are MEDIUM PRIORITY for an AI PM.
These should be FYI updates, meeting reminders, and informational content.

Examples:
- Weekly team updates
- Meeting reminders
- Documentation updates
- Process announcements
- General project status

Make them realistic for an AI PM role. Format as JSON array of message objects with 'text' and 'sender_role' fields.
""",
            
            "low_priority": f"""
Generate {count} realistic Slack messages that are LOW PRIORITY for an AI PM.
These should be casual chat, automated updates, or off-topic discussions.

Examples:
- Casual team chat
- Automated metric reports
- Off-topic discussions
- Social updates
- Non-work related content

Make them realistic. Format as JSON array of message objects with 'text' and 'sender_role' fields.
"""
        }
        
        prompt = category_prompts[category]
        
        try:
            response = self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SIMULATION_CONTEXT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=2000
            )
            
            # Parse JSON response
            content = response.choices[0].message.content
            messages = json.loads(content)
            
            return messages
            
        except Exception as e:
            print(f"❌ Error generating messages for {category}: {e}")
            return []
    
    async def post_messages_to_slack(self, messages, category, channel_id):
        """Post generated messages to Slack using appropriate bots"""
        
        bot_mapping = {
            "manager": self.bots["manager"],
            "engineer": self.bots["coworker"], 
            "data_scientist": self.bots["coworker"],
            "sales": self.bots["coworker"],
            "support": self.bots["coworker"],
            "automated": self.bots["metrics"]
        }
        
        posted_count = 0
        
        for i, msg in enumerate(messages):
            try:
                # Select bot based on sender role
                sender_role = msg.get("sender_role", "engineer")
                bot = bot_mapping.get(sender_role, self.bots["coworker"])
                
                # Post message
                result = bot.chat_postMessage(
                    channel=channel_id,
                    text=msg["text"]
                )
                
                print(f"✅ {category} - {sender_role}: {msg['text'][:50]}...")
                posted_count += 1
                
                # Small delay between messages
                time.sleep(0.5)
                
            except Exception as e:
                print(f"❌ Error posting message: {e}")
        
        return posted_count
    
    async def run_simulation(self, channel_id, messages_per_category=10):
        """Run the full simulation"""
        
        print("🤖 LLM-Powered Simulation Generator")
        print("=" * 60)
        print(f"📋 Generating {messages_per_category} messages per category")
        print(f"📤 Posting to channel: {channel_id}")
        print()
        
        categories = ["critical", "high_priority", "medium_priority", "low_priority"]
        total_messages = 0
        
        for category in categories:
            print(f"🎯 Generating {category} messages...")
            
            # Generate messages
            messages = await self.generate_messages_for_category(category, messages_per_category)
            
            if not messages:
                print(f"❌ Failed to generate messages for {category}")
                continue
            
            # Post to Slack
            posted = await self.post_messages_to_slack(messages, category, channel_id)
            total_messages += posted
            
            print(f"✅ Posted {posted} {category} messages")
            print()
            
            # Delay between categories
            time.sleep(2)
        
        print(f"🎉 Simulation complete! Generated {total_messages} total messages")
        print()
        # Get API port from environment (default 8000)
        api_port = int(os.getenv("API_PORT", "8000"))
        
        print("Next steps:")
        print(f"1. Run: curl -X POST 'http://localhost:{api_port}/api/slack/sync?hours_ago=1'")
        print(f"2. Check: curl -s 'http://localhost:{api_port}/api/slack/inbox?view=all'")
        print("3. Validate prioritization accuracy")

async def main():
    """Main simulation runner"""
    
    # Get channel ID from user
    print("🤖 AI PM Simulation Generator")
    print("=" * 50)
    print("This will generate realistic messages for your AI PM role")
    print("building a conversational virtual sales assistant.")
    print()
    
    channel_id = input("Enter channel ID to post messages to: ").strip()
    
    if not channel_id:
        print("❌ Channel ID required")
        return
    
    if not channel_id.startswith('C'):
        print("❌ Channel ID should start with 'C'")
        return
    
    # Run simulation
    generator = LLMSimulationGenerator()
    await generator.run_simulation(channel_id, messages_per_category=8)

if __name__ == "__main__":
    asyncio.run(main())
