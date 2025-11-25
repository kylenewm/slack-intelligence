"""
Test script for Slack Events API.
Simulates Slack sending an event with a valid signature.
"""

import time
import hmac
import hashlib
import json
import requests
from dotenv import load_dotenv
import os

load_dotenv()

SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
API_URL = "http://localhost:8000/api/slack/events"

def generate_signature(body, timestamp):
    sig_basestring = f"v0:{timestamp}:{body}"
    my_signature = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode("utf-8"),
        sig_basestring.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return my_signature

def test_url_verification():
    print("\n🧪 Testing URL Verification...")
    payload = {
        "token": "Jhj5dZrVaK7ZwHHjRyZWjbDl",
        "challenge": "3eZbrw1aBm2rZgRNFdxV2595E9CY3gmdALWMmHkvFXO7tYXAYM8P",
        "type": "url_verification"
    }
    body = json.dumps(payload)
    timestamp = str(int(time.time()))
    signature = generate_signature(body, timestamp)
    
    headers = {
        "X-Slack-Request-Timestamp": timestamp,
        "X-Slack-Signature": signature,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(API_URL, data=body, headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200 and response.json().get("challenge") == payload["challenge"]:
            print("✅ URL Verification Passed")
        else:
            print("❌ URL Verification Failed")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

def test_message_event():
    print("\n🧪 Testing Message Event...")
    payload = {
        "token": "z26uFts79eilF28HeLM7T1Xl",
        "team_id": "T061EG9R6",
        "api_app_id": "A061EY3R6",
        "event": {
            "type": "message",
            "user": "U061F7AUR",
            "text": "This is a test message from the event API",
            "ts": "1699396522.000000",
            "channel": "C061EG9SL",
            "event_ts": "1699396522.000000",
            "channel_type": "channel"
        },
        "type": "event_callback",
        "event_id": "Ev061F7AUR",
        "event_time": 1699396522
    }
    body = json.dumps(payload)
    timestamp = str(int(time.time()))
    signature = generate_signature(body, timestamp)
    
    headers = {
        "X-Slack-Request-Timestamp": timestamp,
        "X-Slack-Signature": signature,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(API_URL, data=body, headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Message Event Accepted (Processing in background)")
        else:
            print("❌ Message Event Failed")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    if not SLACK_SIGNING_SECRET:
        print("❌ SLACK_SIGNING_SECRET not found in .env")
        exit(1)
        
    print(f"Target: {API_URL}")
    test_url_verification()
    test_message_event()

