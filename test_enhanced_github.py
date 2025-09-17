#!/usr/bin/env python3

import os
import dotenv
from github_tools import init_github_client, get_recent_github_merged_prs, get_recent_github_commits

# Load environment variables
dotenv.load_dotenv()

def test_enhanced_github_analysis():
    """Test the enhanced GitHub analysis functionality."""
    print("🔍 Testing Enhanced GitHub Analysis")
    print("=" * 50)

    # Initialize GitHub client
    try:
        github_token = os.getenv("GITHUB_TOKEN")
        github_org = os.getenv("GITHUB_ORG", "orcasecurity")  # Default org
        github_repo = os.getenv("GITHUB_REPO", "orca")  # Default repo

        if not github_token:
            print("❌ GITHUB_TOKEN not found in environment variables")
            return

        print(f"🔗 Initializing GitHub client for {github_org}/{github_repo}")
        init_github_client(github_token, github_org, github_repo)
        print("✅ GitHub client initialized successfully\n")

    except Exception as e:
        print(f"❌ Failed to initialize GitHub client: {e}")
        return

    # Test enhanced PR analysis
    print("📥 Testing Enhanced PR Analysis")
    print("-" * 30)
    try:
        prs = get_recent_github_merged_prs(hours=168)  # Last week
        print(f"Found {len(prs)} PRs in the last week\n")

        for i, pr in enumerate(prs[:2], 1):  # Show first 2 PRs in detail
            print(f"PR #{i}: #{pr['number']} - {pr['title']}")
            print(f"  Author: {pr['author']}")
            print(f"  Merged: {pr['merged_at']}")
            print(f"  Risk Level: {pr.get('overall_risk', 'unknown')}")
            print(f"  Files Changed: {pr['changed_files']}")

            if pr.get('change_summary'):
                print(f"  Change Summary: {pr['change_summary']}")

            if pr.get('quality_report'):
                print(f"  Quality Report: {pr['quality_report']}")

            # Show detailed file analysis for first few files
            file_analyses = pr.get('file_analyses', [])
            if file_analyses:
                print(f"  📁 File Analysis ({len(file_analyses)} files):")
                for j, file_analysis in enumerate(file_analyses[:3], 1):  # First 3 files
                    print(f"    {j}. {file_analysis.get('filename', 'unknown')} ({file_analysis.get('file_type', 'unknown')})")
                    print(f"       Risk: {file_analysis.get('risk_level', 'unknown')}")
                    print(f"       Summary: {file_analysis.get('summary', 'No summary')}")

                    # Show specific changes if available
                    changes = file_analysis.get('changes', {})
                    if changes.get('functions_added'):
                        print(f"       ➕ Functions Added: {', '.join(changes['functions_added'][:3])}")
                    if changes.get('functions_modified'):
                        print(f"       🔧 Functions Modified: {', '.join(changes['functions_modified'][:3])}")
                    if changes.get('imports_added'):
                        print(f"       📦 Imports Added: {', '.join(changes['imports_added'][:2])}")
                    if changes.get('critical_patterns'):
                        print(f"       🚨 Critical Patterns: {len(changes['critical_patterns'])} found")

            print()

    except Exception as e:
        print(f"❌ Error testing PR analysis: {e}\n")

    # Test enhanced commit analysis
    print("💻 Testing Enhanced Commit Analysis")
    print("-" * 30)
    try:
        commits = get_recent_github_commits(hours=24)  # Last 24 hours
        print(f"Found {len(commits)} commits in the last 24 hours\n")

        for i, commit in enumerate(commits[:2], 1):  # Show first 2 commits in detail
            print(f"Commit #{i}: {commit['sha'][:8]} - {commit['message'].split(chr(10))[0]}")
            print(f"  Author: {commit['author']}")
            print(f"  Time: {commit['committed_at']}")
            print(f"  Risk Level: {commit.get('overall_risk', 'unknown')}")
            print(f"  Files Changed: {commit['files_changed']}")

            if commit.get('change_summary'):
                print(f"  Change Summary: {commit['change_summary']}")

            if commit.get('quality_report'):
                print(f"  Quality Report: {commit['quality_report']}")

            print()

    except Exception as e:
        print(f"❌ Error testing commit analysis: {e}\n")

    print("✅ Enhanced GitHub analysis test completed!")

if __name__ == "__main__":
    test_enhanced_github_analysis()