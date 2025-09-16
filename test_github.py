#!/usr/bin/env python3

import dotenv
import os
from github_tools import init_github_client, get_recent_merged_prs, get_recent_deployments, get_recent_commits, analyze_deployment_correlation

# Load environment variables
dotenv.load_dotenv()

def test_github():
    """Test GitHub integration"""
    print("Testing GitHub integration...")

    try:
        # Initialize client
        github_token = os.getenv("GITHUB_TOKEN")
        github_org = os.getenv("GITHUB_ORG")
        github_repo = os.getenv("GITHUB_REPO")

        if not github_token or github_token == "YOUR_GITHUB_TOKEN":
            print("❌ Please set your actual GITHUB_TOKEN in .env file")
            return

        if not github_org or not github_repo:
            print("❌ Please set GITHUB_ORG and GITHUB_REPO in .env file")
            return

        init_github_client(github_token, github_org, github_repo)
        print(f"✅ GitHub client initialized for {github_org}/{github_repo}")

        # Test getting recent PRs
        print("\n--- Testing get_recent_merged_prs (last 24 hours) ---")
        prs = get_recent_merged_prs(hours=24)
        if prs:
            print(f"Found {len(prs)} recently merged PRs")
            for pr in prs[:3]:  # Show first 3
                print(f"  - PR #{pr['number']}: {pr['title']}")
                print(f"    Merged: {pr['merged_at']} by {pr['author']}")
        else:
            print("No PRs merged in the last 24 hours")

        # Test getting recent deployments
        print("\n--- Testing get_recent_deployments (last 24 hours) ---")
        deployments = get_recent_deployments(hours=24)
        if deployments:
            print(f"Found {len(deployments)} recent deployments")
            for deploy in deployments[:3]:  # Show first 3
                print(f"  - Environment: {deploy['environment']}")
                print(f"    Status: {deploy['status']}")
                print(f"    Created: {deploy['created_at']}")
        else:
            print("No deployments found in the last 24 hours")

        # Test getting recent commits
        print("\n--- Testing get_recent_commits (last 24 hours) ---")
        commits = get_recent_commits(hours=24)
        if commits:
            print(f"Found {len(commits)} recent commits")
            for commit in commits[:3]:  # Show first 3
                print(f"  - {commit['sha'][:8]}: {commit['message'].split(chr(10))[0]}")
                print(f"    Author: {commit['author']}")
        else:
            print("No commits found in the last 24 hours")

        # Test correlation analysis with a sample incident time
        print("\n--- Testing analyze_deployment_correlation ---")
        from datetime import datetime, timezone
        incident_time = datetime.now(timezone.utc).isoformat()

        correlation = analyze_deployment_correlation(incident_time, service="orca", region="us-east-1")
        print("Sample correlation analysis:")
        print(correlation[:500] + "..." if len(correlation) > 500 else correlation)

        print("\n✅ All GitHub tests completed!")

    except Exception as e:
        print(f"❌ Error testing GitHub: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_github()