import os
import json
from typing import Dict, List, Any, Optional
import ldclient
from ldclient.config import Config
from ldclient.context import Context

# Global client instance
_ld_client = None

def init_launchdarkly_client(sdk_key: str):
    """Initialize the LaunchDarkly client with the SDK key."""
    global _ld_client
    if not sdk_key:
        raise ValueError("LaunchDarkly SDK key is required")

    # Set the config first, then get the client
    config = Config(sdk_key=sdk_key)
    ldclient.set_config(config)
    _ld_client = ldclient.get()

    # Wait for client to initialize
    if _ld_client.is_initialized():
        print("LaunchDarkly client initialized successfully")
    else:
        print("Warning: LaunchDarkly client failed to initialize")

def get_launchdarkly_client():
    """Get the initialized LaunchDarkly client."""
    global _ld_client
    if _ld_client is None:
        raise RuntimeError("LaunchDarkly client not initialized. Call init_launchdarkly_client() first.")
    return _ld_client

def get_feature_flag(flag_key: str, user_context: Dict[str, Any] = None, default_value: bool = False) -> bool:
    """
    Get the value of a feature flag for a given user context.

    Args:
        flag_key: The key of the feature flag
        user_context: User context for flag evaluation (optional)
        default_value: Default value if flag evaluation fails

    Returns:
        Boolean value of the feature flag
    """
    try:
        client = get_launchdarkly_client()
        if user_context is None:
            context = Context.builder("sre-agent").name("SRE Operations Agent").build()
        else:
            context = Context.builder(user_context.get("key", "sre-agent")).name(user_context.get("name", "SRE Operations Agent")).build()

        return client.variation(flag_key, context, default_value)
    except Exception as e:
        print(f"Error getting feature flag {flag_key}: {e}")
        return default_value

def get_feature_flag_details(flag_key: str, user_context: Dict[str, Any] = None, default_value: Any = None) -> Dict[str, Any]:
    """
    Get detailed information about a feature flag evaluation.

    Args:
        flag_key: The key of the feature flag
        user_context: User context for flag evaluation (optional)
        default_value: Default value if flag evaluation fails

    Returns:
        Dictionary with flag details including value, variation, and reason
    """
    try:
        client = get_launchdarkly_client()
        if user_context is None:
            context = Context.builder("sre-agent").name("SRE Operations Agent").build()
        else:
            context = Context.builder(user_context.get("key", "sre-agent")).name(user_context.get("name", "SRE Operations Agent")).build()

        detail = client.variation_detail(flag_key, context, default_value)

        return {
            "flag_key": flag_key,
            "value": detail.value,
            "variation_index": detail.variation_index,
            "reason": str(detail.reason),
            "is_default": detail.is_default_value()
        }
    except Exception as e:
        print(f"Error getting feature flag details for {flag_key}: {e}")
        return {
            "flag_key": flag_key,
            "value": default_value,
            "variation_index": None,
            "reason": f"Error: {e}",
            "is_default": True
        }

def check_multiple_flags(flag_keys: List[str], user_context: Dict[str, Any] = None) -> Dict[str, bool]:
    """
    Check multiple feature flags at once.

    Args:
        flag_keys: List of feature flag keys to check
        user_context: User context for flag evaluation (optional)

    Returns:
        Dictionary mapping flag keys to their boolean values
    """
    results = {}
    for flag_key in flag_keys:
        results[flag_key] = get_feature_flag(flag_key, user_context)
    return results

def get_all_flags(user_context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Get all feature flags and their values for the given user context.

    Args:
        user_context: User context for flag evaluation (optional)

    Returns:
        Dictionary of all flags and their values
    """
    try:
        client = get_launchdarkly_client()
        if user_context is None:
            context = Context.builder("sre-agent").name("SRE Operations Agent").build()
        else:
            context = Context.builder(user_context.get("key", "sre-agent")).name(user_context.get("name", "SRE Operations Agent")).build()

        return client.all_flags_state(context).to_values_map()
    except Exception as e:
        print(f"Error getting all flags: {e}")
        return {}

def track_custom_event(event_name: str, user_context: Dict[str, Any] = None, data: Dict[str, Any] = None):
    """
    Track a custom event in LaunchDarkly.

    Args:
        event_name: Name of the custom event
        user_context: User context (optional)
        data: Additional data to include with the event (optional)
    """
    try:
        client = get_launchdarkly_client()
        if user_context is None:
            context = Context.builder("sre-agent").name("SRE Operations Agent").build()
        else:
            context = Context.builder(user_context.get("key", "sre-agent")).name(user_context.get("name", "SRE Operations Agent")).build()

        client.track(event_name, context, data)
        print(f"Tracked custom event: {event_name}")
    except Exception as e:
        print(f"Error tracking custom event {event_name}: {e}")

def close_launchdarkly_client():
    """Close the LaunchDarkly client and flush any pending events."""
    global _ld_client
    if _ld_client:
        _ld_client.close()
        _ld_client = None
        print("LaunchDarkly client closed")

# Agent tool functions (these will be used by the AI agent)

def get_all_feature_flags() -> str:
    """Get all feature flags and their current status."""
    try:
        all_flags = get_all_flags()
        if not all_flags:
            return "No feature flags found or LaunchDarkly client not properly initialized."

        result = f"All Feature Flags ({len(all_flags)} total):\n"
        for flag_key, value in all_flags.items():
            result += f"- {flag_key}: {value}\n"

        return result
    except Exception as e:
        return f"Error retrieving feature flags: {e}"

def check_sre_flag(flag_key: str) -> str:
    """Check the status of a specific SRE feature flag."""
    try:
        details = get_feature_flag_details(flag_key)
        return f"Feature flag '{flag_key}':\n" \
               f"- Value: {details['value']}\n" \
               f"- Variation: {details['variation_index']}\n" \
               f"- Reason: {details['reason']}\n" \
               f"- Using default: {details['is_default']}"
    except Exception as e:
        return f"Error checking feature flag '{flag_key}': {e}"

def enable_maintenance_mode() -> str:
    """Check if maintenance mode is enabled via feature flag."""
    try:
        is_enabled = get_feature_flag("maintenance-mode", default_value=False)
        if is_enabled:
            track_custom_event("maintenance_mode_checked", data={"status": "enabled"})
            return "🚨 Maintenance mode is ENABLED. Some SRE operations may be restricted."
        else:
            track_custom_event("maintenance_mode_checked", data={"status": "disabled"})
            return "✅ Maintenance mode is disabled. Normal operations active."
    except Exception as e:
        return f"Error checking maintenance mode: {e}"

def get_alert_thresholds() -> str:
    """Get current alert thresholds from feature flags."""
    try:
        # These would be JSON flags or numeric flags in your LaunchDarkly setup
        cpu_threshold = get_feature_flag("cpu-alert-threshold", default_value=80)
        memory_threshold = get_feature_flag("memory-alert-threshold", default_value=85)
        disk_threshold = get_feature_flag("disk-alert-threshold", default_value=90)

        return f"Current Alert Thresholds:\n" \
               f"- CPU: {cpu_threshold}%\n" \
               f"- Memory: {memory_threshold}%\n" \
               f"- Disk: {disk_threshold}%"
    except Exception as e:
        return f"Error getting alert thresholds: {e}"