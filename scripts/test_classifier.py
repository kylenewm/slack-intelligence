#!/usr/bin/env python3
"""
Test the Exa research classifier with diverse examples.
Shows: needs_research (true/false) and reason
Does NOT trigger actual Exa research.
"""

import asyncio
import sys
sys.path.insert(0, '/Users/kylenewman/slack-intelligence-updated')

from backend.integrations.exa_service import ExaSearchService

# Diverse test messages
TEST_MESSAGES = [
    # Should trigger research (external tech questions)
    {"text": "Should we use Pinecone or pgvector for our vector database?", "channel_name": "engineering", "user_name": "Dev"},
    {"text": "What's the best practice for rate limiting APIs?", "channel_name": "engineering", "user_name": "Dev"},
    {"text": "Comparing Auth0 vs Okta for SSO - thoughts?", "channel_name": "engineering", "user_name": "Dev"},
    {"text": "What's the industry standard for API pagination?", "channel_name": "engineering", "user_name": "Dev"},
    {"text": "Redis vs Memcached for session storage?", "channel_name": "engineering", "user_name": "Dev"},
    {"text": "Looking into feature flags - LaunchDarkly vs Split?", "channel_name": "product", "user_name": "PM"},
    {"text": "What are best practices for microservices communication?", "channel_name": "engineering", "user_name": "Dev"},
    {"text": "Stripe vs Braintree for payment processing?", "channel_name": "product", "user_name": "PM"},
    {"text": "What's the recommended approach for database migrations at scale?", "channel_name": "engineering", "user_name": "Dev"},
    {"text": "GraphQL vs REST for our new API - what do companies our size use?", "channel_name": "engineering", "user_name": "Dev"},
    
    # Should NOT trigger research (internal tasks)
    {"text": "Can you put together a comparison doc with cost projections?", "channel_name": "product", "user_name": "PM"},
    {"text": "We need to figure out the roadmap for Q4", "channel_name": "product", "user_name": "PM"},
    {"text": "Let's schedule a meeting to discuss the budget", "channel_name": "general", "user_name": "Manager"},
    {"text": "Please update the Jira ticket with the latest status", "channel_name": "engineering", "user_name": "Dev"},
    {"text": "Don't forget the standup at 10am", "channel_name": "engineering", "user_name": "Dev"},
    {"text": "I'll be OOO tomorrow", "channel_name": "general", "user_name": "Employee"},
    {"text": "Great work on the release everyone!", "channel_name": "general", "user_name": "Manager"},
    {"text": "Who's working on the login bug?", "channel_name": "engineering", "user_name": "Dev"},
    {"text": "The deploy is done, monitoring now", "channel_name": "engineering", "user_name": "Dev"},
    {"text": "Lunch at noon anyone?", "channel_name": "watercooler", "user_name": "Employee"},
    
    # Should NOT trigger (bugs - use bug analyzer)
    {"text": "500 error on /api/users endpoint after deploy", "channel_name": "incidents", "user_name": "AlertBot"},
    {"text": "TypeError: Cannot read property 'id' of undefined in auth.js", "channel_name": "engineering", "user_name": "Dev"},
    {"text": "Database connection timeout errors spiking", "channel_name": "incidents", "user_name": "Metrics"},
    {"text": "Memory leak in the worker process", "channel_name": "engineering", "user_name": "Dev"},
    {"text": "API returning 429 rate limit errors", "channel_name": "incidents", "user_name": "AlertBot"},
    
    # Edge cases - might or might not need research
    {"text": "How do other companies handle GDPR compliance?", "channel_name": "legal", "user_name": "Legal"},
    {"text": "What's the typical SLA for enterprise customers?", "channel_name": "sales", "user_name": "Sales"},
    {"text": "Should we use WebSockets or SSE for real-time updates?", "channel_name": "engineering", "user_name": "Dev"},
    {"text": "What monitoring tools do startups typically use?", "channel_name": "engineering", "user_name": "Dev"},
    {"text": "How should we structure our pricing tiers?", "channel_name": "product", "user_name": "PM"},
    
    # More internal/vague
    {"text": "Let's sync on this tomorrow", "channel_name": "general", "user_name": "Manager"},
    {"text": "Can someone review my PR?", "channel_name": "engineering", "user_name": "Dev"},
    {"text": "The customer is asking about timelines", "channel_name": "sales", "user_name": "Sales"},
    {"text": "We need to improve our onboarding flow", "channel_name": "product", "user_name": "PM"},
    {"text": "Sales numbers look good this quarter", "channel_name": "general", "user_name": "CEO"},
    
    # More specific tech questions
    {"text": "Kubernetes vs ECS for container orchestration?", "channel_name": "devops", "user_name": "DevOps"},
    {"text": "What's the best way to implement circuit breakers?", "channel_name": "engineering", "user_name": "Dev"},
    {"text": "Terraform vs Pulumi for IaC?", "channel_name": "devops", "user_name": "DevOps"},
    {"text": "How do you handle secrets management in production?", "channel_name": "devops", "user_name": "DevOps"},
    {"text": "Jest vs Vitest for testing React apps?", "channel_name": "engineering", "user_name": "Dev"},
    
    # Customer issues
    {"text": "Customer Acme Corp says they can't login", "channel_name": "support", "user_name": "Support"},
    {"text": "Enterprise customer asking about SOC2 compliance", "channel_name": "sales", "user_name": "Sales"},
    {"text": "User reported slow load times on dashboard", "channel_name": "support", "user_name": "Support"},
    
    # Meeting/status updates
    {"text": "Sprint retro notes: we need better testing", "channel_name": "engineering", "user_name": "Scrum"},
    {"text": "All-hands recording is up on Notion", "channel_name": "general", "user_name": "HR"},
    {"text": "Release 2.4.1 deployed to production", "channel_name": "releases", "user_name": "CI Bot"},
]

async def run_classifier():
    service = ExaSearchService()
    
    if not service.openai_client:
        print("ERROR: OpenAI client not available")
        return
    
    print("=" * 100)
    print(f"{'#':<3} {'RESEARCH':<8} {'TYPE':<20} {'MESSAGE':<40} {'REASON'}")
    print("=" * 100)
    
    true_count = 0
    false_count = 0
    
    for i, msg in enumerate(TEST_MESSAGES, 1):
        try:
            result = await service.detect_ticket_type(msg)
            needs = result.get('needs_research', False)
            ticket_type = result.get('ticket_type', 'unknown')
            reason = result.get('reason', 'N/A')[:50]
            
            if needs:
                true_count += 1
                flag = "✅ YES"
            else:
                false_count += 1
                flag = "❌ NO"
            
            text_preview = msg['text'][:38] + ".." if len(msg['text']) > 40 else msg['text']
            print(f"{i:<3} {flag:<8} {ticket_type:<20} {text_preview:<40} {reason}")
            
        except Exception as e:
            print(f"{i:<3} ERROR: {e}")
    
    print("=" * 100)
    print(f"SUMMARY: {true_count} need research, {false_count} don't need research")
    print(f"Total: {len(TEST_MESSAGES)} messages")

if __name__ == "__main__":
    asyncio.run(run_classifier())
