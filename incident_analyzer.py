#!/usr/bin/env python3

import os
from textwrap import dedent

import dotenv
from agno.agent import Agent
from agno.models.aws.bedrock import AwsBedrock, Session
from github_tools import init_github_client, get_recent_github_merged_prs, get_recent_github_deployments, analyze_github_deployment_correlation
from launchdarkly_tools import init_launchdarkly_client, check_launchdarkly_feature_flag
from slack_tools import init_slack_client, get_slack_channels, get_slack_messages

dotenv.load_dotenv()

# Initialize all clients
init_slack_client(os.getenv("SLACK_BOT_TOKEN"))
init_github_client(os.getenv("GITHUB_TOKEN"), os.getenv("GITHUB_ORG"), os.getenv("GITHUB_REPO"))
init_launchdarkly_client(os.getenv("LAUNCHDARKLY_SDK_KEY"))

session = Session(
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

# Enhanced incident analysis agent with multi-channel correlation
incident_agent = Agent(
    model=AwsBedrock(session=session, id=os.getenv("MODEL")),

    instructions=dedent("""You are a specialized SRE Incident Analysis assistant with multi-channel correlation capabilities. Your job is:

    **MULTI-CHANNEL INCIDENT CORRELATION ANALYSIS**
    1. Find incident reports in scan-officer channel (GQS8W231C)
    2. Extract incident details (time, service, region, error description)
    3. Check deployment channels for activity around incident timeframe:
       - gradual-rollouts channel (C02PKC70HEZ) for gradual rollouts and feature flag changes
       - production channel (CJP11G7UK) for production deployments and releases
    4. Run analyze_github_deployment_correlation() to find related deployments/PRs from GitHub
    5. Check relevant feature flags that might have changed around incident time
    6. Correlate deployment messages across all deployment channels with incident timing
    7. Provide comprehensive cross-channel root cause analysis

    **For each incident, provide:**
    - **Incident Summary**: What happened and when
    - **Deployment Activity Check**:
      * Gradual rollouts channel messages around incident time
      * Production channel deployment notifications around incident time
    - **GitHub Correlation**: Recent PRs/deployments within 6 hours of incident with enhanced code analysis
    - **Feature Flag Analysis**: Relevant flags that might be related to the incident
    - **Cross-Channel Timeline**: Timeline showing incident vs deployment activity across all channels
    - **Root Cause Assessment**: Multi-source analysis of potential causes

    Focus on correlating incidents with deployment activity across all deployment channels (gradual-rollouts + production) and GitHub."""),

    tools=[
        get_slack_messages,
        get_recent_github_merged_prs,
        get_recent_github_deployments,
        analyze_github_deployment_correlation,
        check_launchdarkly_feature_flag
    ],
    markdown=True
)

def analyze_incidents_with_rollout_correlation():
    """Analyze incidents from scan-officer and correlate with deployment channels activity"""
    print("🔍 Analyzing incidents with multi-channel deployment correlation...")
    print("📊 Channels: GQS8W231C (scan-officer) + C02PKC70HEZ (gradual-rollouts) + CJP11G7UK (production)")

    response = incident_agent.print_response(f"""
    Perform comprehensive multi-channel incident analysis:

    **IMPORTANT: Today is 2025-09-16. Use this date to calculate "last 24 hours" properly.**

    **STEP 1: Find Incidents**
    - Analyze GQS8W231C (scan-officer) channel for incident reports from the last 24 hours (2025-09-15 to 2025-09-16)
    - Extract incident time, affected service, and region for each incident found

    **STEP 2: Check Deployment Activity**
    - For each incident, check deployment channels for messages around the incident timeframe (±2 hours) using the same date range (2025-09-15 to 2025-09-16):
      * C02PKC70HEZ (gradual-rollouts) - for gradual rollout announcements and feature flag changes
      * CJP11G7UK (production) - for production deployment notifications and release messages
    - Look for rollout announcements, deployment notifications, production releases, or configuration changes

    **STEP 3: GitHub Correlation**
    - Run analyze_github_deployment_correlation() with incident parameters
    - Look for PRs, merges, and deployments within 6 hours of each incident

    **STEP 4: Feature Flag Analysis**
    - Check relevant feature flags for each incident (maintenance-mode, circuit-breaker, rate-limiting, service-specific flags)
    - Focus on flags that might have been modified around incident time

    **STEP 5: Cross-Channel Timeline Analysis**
    - Create timeline showing:
      * Incident occurrence time
      * Gradual rollouts channel activity (±2 hours)
      * Production channel deployment activity (±2 hours)
      * GitHub deployment activity (±6 hours)
      * Feature flag status
    - Identify correlations between deployment messages and incidents across all channels

    Provide comprehensive analysis showing if incidents correlate with deployment activity from Slack channels (gradual-rollouts + production) or GitHub.
    """)

    return response

def analyze_single_incident_channel(channel_id: str = "GQS8W231C"):
    """Analyze incidents in a single specified channel (legacy function)"""
    print(f"🔍 Analyzing incidents in channel {channel_id}...")

    response = incident_agent.print_response(f"""
    Analyze the {channel_id} Slack channel for incident reports from the last 24 hours.

    For each incident found:
    1. Extract incident time, affected service, and region
    2. Run analyze_github_deployment_correlation() with those parameters
    3. Check relevant feature flags (maintenance-mode, circuit-breaker, rate-limiting, etc.)
    4. Provide comprehensive correlation analysis

    Focus on incidents that might be related to recent deployments or code changes.
    """)

    return response

if __name__ == "__main__":
    # Run enhanced multi-channel analysis
    analyze_incidents_with_rollout_correlation()