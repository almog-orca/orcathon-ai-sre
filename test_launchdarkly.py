#!/usr/bin/env python3

import dotenv
import os
from launchdarkly_tools import init_launchdarkly_client, get_all_feature_flags, check_feature_flag, enable_maintenance_mode, get_alert_thresholds

# Load environment variables
dotenv.load_dotenv()

def test_launchdarkly():
    """Test LaunchDarkly integration"""
    print("Testing LaunchDarkly integration...")

    try:
        # Initialize client
        sdk_key = os.getenv("LAUNCHDARKLY_SDK_KEY")
        if not sdk_key or sdk_key == "YOUR_LAUNCHDARKLY_SDK_KEY":
            print("❌ Please set your actual LAUNCHDARKLY_SDK_KEY in .env file")
            return

        init_launchdarkly_client(sdk_key)
        print("✅ LaunchDarkly client initialized")

        # Test getting all feature flags
        print("\n--- Testing get_all_feature_flags ---")
        flags = get_all_feature_flags()
        print(flags)

        # Test checking specific flag
        print("\n--- Testing check_feature_flag ---")
        flag_status = check_feature_flag("maintenance-mode")
        print(flag_status)

        # Test maintenance mode
        print("\n--- Testing maintenance mode ---")
        maintenance = enable_maintenance_mode()
        print(maintenance)

        # Test alert thresholds
        print("\n--- Testing alert thresholds ---")
        thresholds = get_alert_thresholds()
        print(thresholds)

        print("\n✅ All tests completed!")

    except Exception as e:
        print(f"❌ Error testing LaunchDarkly: {e}")

if __name__ == "__main__":
    test_launchdarkly()