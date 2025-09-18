#!/usr/bin/env python3

import os
import dotenv
from datetime import datetime, timedelta
from slack_tools import init_slack_client, get_slack_messages

dotenv.load_dotenv()

def test_fixed_retrieval():
    """Test the fixed message retrieval."""
    print("🔧 Testing Fixed Message Retrieval")
    print("=" * 50)

    init_slack_client(os.getenv("SLACK_BOT_TOKEN"))
    channel_id = "C076NHGBK8E"

    # Test the fixed approach
    today = datetime.now().strftime("%Y-%m-%d")
    three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

    print(f"Using fixed get_slack_messages function")
    print(f"Date range: {three_days_ago} to {today}")
    print(f"Limit: 500")

    try:
        # This should now use the fixed version that includes full day
        messages = get_slack_messages(
            channel_id=channel_id,
            start_date=three_days_ago,
            end_date=today,
            limit=500
        )

        print(f"Got {len(messages)} messages")

        if messages:
            print("Most recent messages:")
            for i, msg in enumerate(messages[:10]):
                ts = float(msg.get("ts", 0))
                dt = datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
                text = msg.get("text", "No text")[:80]

                # Highlight messages newer than Sept 17 04:08 (lululemon Shanghai)
                lululemon_time = datetime(2025, 9, 17, 4, 8, tzinfo=datetime.timezone.utc)
                if dt > lululemon_time:
                    print(f"  🆕 {i+1}. [{dt.strftime('%m-%d %H:%M')}] {text}...")
                else:
                    print(f"     {i+1}. [{dt.strftime('%m-%d %H:%M')}] {text}...")

        else:
            print("❌ No messages retrieved")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fixed_retrieval()