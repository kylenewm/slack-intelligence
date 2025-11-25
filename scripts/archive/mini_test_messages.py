import os
import time
from slack_sdk import WebClient
from dotenv import load_dotenv

# Load local env to get tokens
load_dotenv()

# Use personal token if available, otherwise default
token = os.getenv("SLACK_BOT_TOKEN_PERSONAL") or os.getenv("SLACK_BOT_TOKEN")
client = WebClient(token=token)

# Find a channel to post to (general or random)
def get_channel_id():
    try:
        response = client.conversations_list(types="public_channel")
        for channel in response["channels"]:
            if channel["name"] in ["general", "testing", "random"]:
                return channel["id"]
        return response["channels"][0]["id"]
    except Exception as e:
        print(f"Error finding channel: {e}")
        return None

channel_id = get_channel_id()
if not channel_id:
    print("Could not find a channel to post to.")
    exit(1)

print(f"Posting test messages to channel: {channel_id}")

# Message 1: URGENT BUG (Should trigger Notion + Alert)
print("1. Posting Urgent Bug...")
client.chat_postMessage(
    channel=channel_id,
    text="🚨 CRITICAL: Production database is locking up! Customers are getting 500 errors on checkout. @channel needs immediate attention."
)
time.sleep(2)

# Message 2: RESEARCH REQUEST (Should trigger Exa)
print("2. Posting Research Request...")
client.chat_postMessage(
    channel=channel_id,
    text="We need to decide between Auth0 and Clerk for the new authentication flow. Can someone research the pricing comparison and ease of integration for a FastAPI backend?"
)
time.sleep(2)

# Message 3: FYI (Should be low priority)
print("3. Posting Low Priority Update...")
client.chat_postMessage(
    channel=channel_id,
    text="Just a heads up, I updated the README with the new logo. No action needed."
)

print("\n✅ Messages posted! Now trigger a sync on Railway:")
print("curl -X POST 'https://slack-automation-production.up.railway.app/api/slack/sync?hours_ago=1'")

