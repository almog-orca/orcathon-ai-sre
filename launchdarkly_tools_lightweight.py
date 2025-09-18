#!/usr/bin/env python3

import os
import ldclient
from ldclient.config import Config

# Global client storage
_ld_client = None

def init_launchdarkly_client(sdk_key: str):
    """Initialize LaunchDarkly client for incident analysis"""
    global _ld_client
    try:
        if sdk_key:
            config = Config(sdk_key=sdk_key)
            _ld_client = ldclient.get()
            ldclient.set_config(config)
            print("LaunchDarkly client initialized successfully")
        else:
            print("Warning: LaunchDarkly SDK key not provided")
    except Exception as e:
        print(f"Warning: LaunchDarkly client failed to initialize: {e}")

def check_launchdarkly_feature_flag(flag_key: str, user_key: str = "incident-analyzer") -> str:
    """Check feature flag status for incident correlation"""
    if not _ld_client:
        return f"❌ LaunchDarkly client not initialized"

    try:
        user = {
            "key": user_key,
            "custom": {
                "source": "incident-analyzer"
            }
        }

        flag_value = _ld_client.variation(flag_key, user, False)

        result = f"🚩 **Feature Flag Check**\n"
        result += f"Flag: {flag_key}\n"
        result += f"Status: {'ENABLED' if flag_value else 'DISABLED'}\n"
        result += f"Value: {flag_value}"

        return result

    except Exception as e:
        return f"❌ Error checking feature flag {flag_key}: {str(e)}"

def get_maintenance_mode_status() -> str:
    """Check common maintenance mode flags"""
    common_flags = [
        "maintenance-mode",
        "circuit-breaker",
        "rate-limiting",
        "emergency-mode"
    ]

    results = []
    for flag in common_flags:
        result = check_launchdarkly_feature_flag(flag)
        results.append(result)

    return "\n\n".join(results)