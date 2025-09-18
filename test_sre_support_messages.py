#!/usr/bin/env python3

import os
import dotenv
from datetime import datetime, timedelta
from slack_tools import init_slack_client, get_slack_messages

# Load environment variables
dotenv.load_dotenv()

def test_sre_support_messages():
    """Test retrieving messages from sre-support channel to debug the issue."""
    print("🔍 Testing SRE Support Channel Message Retrieval")
    print("=" * 50)

    # Initialize Slack client
    try:
        slack_token = os.getenv("SLACK_BOT_TOKEN")
        if not slack_token:
            print("❌ SLACK_BOT_TOKEN not found in environment variables")
            return

        print("🔗 Initializing Slack client...")
        init_slack_client(slack_token)
        print("✅ Slack client initialized successfully\n")

    except Exception as e:
        print(f"❌ Failed to initialize Slack client: {e}")
        return

    # Test different time ranges
    channel_id = "C076NHGBK8E"  # sre-support channel

    print(f"📋 Testing message retrieval from channel {channel_id}")

    # Calculate date ranges
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    print(f"Today: {today}")
    print(f"Yesterday: {yesterday}")
    print(f"3 days ago: {three_days_ago}")
    print(f"Week ago: {week_ago}\n")

    # Test 1: Last 24 hours with high limit
    print("📅 TEST 1: Last 24 hours (limit 200)")
    try:
        messages_24h = get_slack_messages(
            channel_id=channel_id,
            start_date=yesterday,
            end_date=today,
            limit=200
        )
        print(f"Found {len(messages_24h)} messages in last 24 hours")
        if messages_24h:
            print("Most recent messages:")
            for i, msg in enumerate(messages_24h[:5]):
                print(f"  {i+1}. {msg.get('user', 'Unknown')}: {msg.get('text', 'No text')[:100]}...")
        print()
    except Exception as e:
        print(f"Error: {e}\n")

    # Test 2: Last 3 days with high limit
    print("📅 TEST 2: Last 3 days (limit 500)")
    try:
        messages_3d = get_slack_messages(
            channel_id=channel_id,
            start_date=three_days_ago,
            end_date=today,
            limit=500
        )
        print(f"Found {len(messages_3d)} messages in last 3 days")
        if messages_3d:
            print("Most recent messages:")
            for i, msg in enumerate(messages_3d[:10]):
                timestamp = msg.get('ts', 'No timestamp')
                user = msg.get('user', 'Unknown')
                text = msg.get('text', 'No text')[:100]
                print(f"  {i+1}. [{timestamp}] {user}: {text}...")
        print()
    except Exception as e:
        print(f"Error: {e}\n")

    # Test 3: Last week with very high limit
    print("📅 TEST 3: Last week (limit 1000)")
    try:
        messages_week = get_slack_messages(
            channel_id=channel_id,
            start_date=week_ago,
            end_date=today,
            limit=1000
        )
        print(f"Found {len(messages_week)} messages in last week")
        if messages_week:
            print("Sample of messages (showing text content):")
            for i, msg in enumerate(messages_week[:15]):
                text = msg.get('text', 'No text')
                if 'lululemon' in text.lower():
                    print(f"  🏷️  LULULEMON: {text[:150]}...")
                elif text and len(text.strip()) > 10:  # Skip very short messages
                    print(f"  {i+1}. {text[:100]}...")
        print()
    except Exception as e:
        print(f"Error: {e}\n")

    print("✅ Message retrieval test completed!")

if __name__ == "__main__":
    test_sre_support_messages()