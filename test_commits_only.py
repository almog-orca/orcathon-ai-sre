#!/usr/bin/env python3

import os
import dotenv
from github_tools import init_github_client, get_recent_github_commits

# Load environment variables
dotenv.load_dotenv()

def test_commits_only():
    """Test just the commit analysis functionality."""
    print("🔍 Testing Commit Analysis Only")
    print("=" * 40)

    # Initialize GitHub client
    try:
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            print("❌ GITHUB_TOKEN not found")
            return

        print("🔗 Initializing GitHub client...")
        init_github_client(github_token, "orcasecurity", "orca")
        print("✅ GitHub client initialized\n")

    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return

    # Test commit analysis with very short timeframe
    print("💻 Testing Commit Analysis (6 hours)")
    print("-" * 30)
    try:
        commits = get_recent_github_commits(hours=6)  # Very short timeframe
        print(f"✅ Successfully retrieved {len(commits)} commits")

        if commits:
            print(f"\nFirst commit details:")
            commit = commits[0]
            print(f"  SHA: {commit['sha'][:8]}")
            print(f"  Message: {commit['message'].split(chr(10))[0]}")
            print(f"  Author: {commit['author']}")
            print(f"  Risk: {commit.get('overall_risk', 'unknown')}")
        else:
            print("No commits found in the last 6 hours")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_commits_only()