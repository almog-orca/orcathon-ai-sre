#!/usr/bin/env python3

import os
from datetime import datetime, timezone

import dotenv
from github_tools import init_github_client, analyze_github_deployment_correlation
from launchdarkly_tools import init_launchdarkly_client, check_feature_flag

# Load environment variables
dotenv.load_dotenv()

def test_incident_correlation():
    """Test incident correlation analysis with simulated incident"""
    print("🚨 Testing Incident Correlation Analysis...")

    # Initialize clients
    init_github_client(os.getenv("GITHUB_TOKEN"), os.getenv("GITHUB_ORG"), os.getenv("GITHUB_REPO"))
    init_launchdarkly_client(os.getenv("LAUNCHDARKLY_SDK_KEY"))

    # Simulate an incident that happened 2 hours ago
    incident_time = "2025-09-16T21:00:00+00:00"  # 9 PM UTC
    service = "orca-api"
    region = "us-east-1"

    print(f"\n🔍 **SIMULATED INCIDENT**")
    print(f"Time: {incident_time}")
    print(f"Service: {service}")
    print(f"Region: {region}")
    print(f"Issue: API response time increased to 5+ seconds")

    print(f"\n" + "="*60)
    print("🔎 **DEPLOYMENT CORRELATION ANALYSIS**")
    print("="*60)

    # Run correlation analysis
    correlation_report = analyze_github_deployment_correlation(incident_time, service, region)
    print(correlation_report)

    print(f"\n" + "="*60)
    print("🏁 **FEATURE FLAG ANALYSIS**")
    print("="*60)

    # Check some relevant feature flags
    flags_to_check = ["maintenance-mode", "api-rate-limiting", "circuit-breaker-enabled"]

    for flag in flags_to_check:
        try:
            flag_status = check_feature_flag(flag)
            print(f"• {flag}: {flag_status}")
        except Exception as e:
            print(f"• {flag}: Could not check ({e})")

    print(f"\n✅ **Incident Analysis Complete!**")
    print("This demonstrates how your system correlates incidents with:")
    print("- Recent deployments and PRs from GitHub")
    print("- Feature flag status from LaunchDarkly")
    print("- Timeline-based root cause analysis")

if __name__ == "__main__":
    test_incident_correlation()