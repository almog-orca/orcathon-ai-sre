#!/usr/bin/env python3
"""
Test script to simulate Slack mention events and verify the bot is working.
"""

import requests
import json
import time

def test_slack_bot():
    """Test the Slack bot with a simulated mention event."""
    
    # Bot URL
    bot_url = "http://localhost:3000"
    
    # First, check if bot is healthy
    try:
        health_response = requests.get(f"{bot_url}/health")
        print("🏥 Health Check:")
        print(f"   Status: {health_response.status_code}")
        print(f"   Response: {health_response.json()}")
        print()
    except Exception as e:
        print(f"❌ Bot not running: {e}")
        return
    
    # Simulate a Slack mention event
    slack_event = {
        "type": "event_callback",
        "event": {
            "type": "app_mention",
            "user": "U1234567890",
            "text": "<@U0BOTUSER> Hello from test! This is a simulated mention.",
            "ts": str(time.time()),
            "channel": "C1234567890"
        }
    }
    
    # Headers to simulate Slack request
    headers = {
        "Content-Type": "application/json",
        "X-Slack-Request-Timestamp": str(int(time.time())),
        "X-Slack-Signature": "v0=test_signature"
    }
    
    print("🤖 Testing Slack Bot Mention Event...")
    print(f"   Sending event: {slack_event['event']['text']}")
    print()
    
    try:
        # Send the simulated event
        response = requests.post(
            f"{bot_url}/slack/events",
            json=slack_event,
            headers=headers
        )
        
        print(f"📡 Bot Response:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        if response.status_code == 200:
            print("\n✅ Test successful! Check the bot terminal output for the mention details.")
        else:
            print(f"\n❌ Test failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing bot: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 SLACK BOT TEST")
    print("=" * 60)
    test_slack_bot()
    print("=" * 60)
