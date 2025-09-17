import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from github import Github, Auth
import requests

# Global client instance
_github_client = None

def init_github_client(token: str, org: str = None, repo: str = None):
    """Initialize the GitHub client with the access token."""
    global _github_client
    if not token:
        raise ValueError("GitHub token is required")

    auth = Auth.Token(token)
    _github_client = Github(auth=auth)

    # Store org and repo for easy access
    _github_client._org_name = org
    _github_client._repo_name = repo

    try:
        # Test the connection
        user = _github_client.get_user()
        print(f"GitHub client initialized successfully for user: {user.login}")
    except Exception as e:
        print(f"Warning: GitHub client failed to initialize: {e}")

def get_github_client():
    """Get the initialized GitHub client."""
    global _github_client
    if _github_client is None:
        raise RuntimeError("GitHub client not initialized. Call init_github_client() first.")
    return _github_client

def get_recent_github_merged_prs(hours: int = 24, repo: str = None) -> List[Dict[str, Any]]:
    """
    Get recently merged pull requests.

    Args:
        hours: Number of hours to look back (default 24)
        repo: Repository name (format: "owner/repo", optional)

    Returns:
        List of PR information dictionaries
    """
    try:
        client = get_github_client()

        # Use provided repo or default from client
        if repo:
            repository = client.get_repo(repo)
        elif hasattr(client, '_org_name') and hasattr(client, '_repo_name') and client._org_name and client._repo_name:
            repository = client.get_repo(f"{client._org_name}/{client._repo_name}")
        else:
            return []

        # Calculate time threshold
        since_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Get recently merged PRs
        pulls = repository.get_pulls(state='closed', sort='updated', direction='desc')

        recent_prs = []
        for pr in pulls:
            if pr.merged_at and pr.merged_at >= since_time:
                recent_prs.append({
                    'number': pr.number,
                    'title': pr.title,
                    'url': pr.html_url,
                    'merged_at': pr.merged_at.isoformat(),
                    'author': pr.user.login,
                    'branch': pr.head.ref,
                    'base_branch': pr.base.ref,
                    'commits': pr.commits,
                    'changed_files': pr.changed_files,
                    'additions': pr.additions,
                    'deletions': pr.deletions,
                    'labels': [label.name for label in pr.labels]
                })
            elif pr.updated_at < since_time:
                # PRs are sorted by updated date, so we can break early
                break

        return recent_prs

    except Exception as e:
        print(f"Error getting recent PRs: {e}")
        return []

def get_recent_github_deployments(hours: int = 24, repo: str = None, environment: str = None) -> List[Dict[str, Any]]:
    """
    Get recent deployments from GitHub.

    Args:
        hours: Number of hours to look back (default 24)
        repo: Repository name (format: "owner/repo", optional)
        environment: Filter by environment (e.g., "production", "staging")

    Returns:
        List of deployment information dictionaries
    """
    try:
        client = get_github_client()

        # Use provided repo or default from client
        if repo:
            repository = client.get_repo(repo)
        elif hasattr(client, '_org_name') and hasattr(client, '_repo_name') and client._org_name and client._repo_name:
            repository = client.get_repo(f"{client._org_name}/{client._repo_name}")
        else:
            return []

        # Calculate time threshold
        since_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Get recent deployments
        deployments = repository.get_deployments()

        recent_deployments = []
        for deployment in deployments:
            if deployment.created_at >= since_time:
                # Filter by environment if specified
                if environment and deployment.environment != environment:
                    continue

                # Get deployment status
                statuses = list(deployment.get_statuses())
                latest_status = statuses[0] if statuses else None

                recent_deployments.append({
                    'id': deployment.id,
                    'sha': deployment.sha,
                    'ref': deployment.ref,
                    'environment': deployment.environment,
                    'created_at': deployment.created_at.isoformat(),
                    'updated_at': deployment.updated_at.isoformat() if deployment.updated_at else None,
                    'creator': deployment.creator.login if deployment.creator else None,
                    'description': deployment.description,
                    'status': latest_status.state if latest_status else 'unknown',
                    'status_description': latest_status.description if latest_status else None,
                    'deployment_url': deployment.url
                })
            else:
                # Deployments are sorted by creation date, so we can break early
                break

        return recent_deployments

    except Exception as e:
        print(f"Error getting recent deployments: {e}")
        return []

def get_recent_github_commits(hours: int = 24, repo: str = None, branch: str = "main") -> List[Dict[str, Any]]:
    """
    Get recent commits to a repository.

    Args:
        hours: Number of hours to look back (default 24)
        repo: Repository name (format: "owner/repo", optional)
        branch: Branch name to check (default "main")

    Returns:
        List of commit information dictionaries
    """
    try:
        client = get_github_client()

        # Use provided repo or default from client
        if repo:
            repository = client.get_repo(repo)
        elif hasattr(client, '_org_name') and hasattr(client, '_repo_name') and client._org_name and client._repo_name:
            repository = client.get_repo(f"{client._org_name}/{client._repo_name}")
        else:
            return []

        # Calculate time threshold
        since_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Get recent commits
        commits = repository.get_commits(sha=branch, since=since_time)

        recent_commits = []
        for commit in commits:
            recent_commits.append({
                'sha': commit.sha,
                'message': commit.commit.message,
                'author': commit.commit.author.name,
                'author_email': commit.commit.author.email,
                'committer': commit.commit.committer.name,
                'committed_at': commit.commit.committer.date.isoformat(),
                'url': commit.html_url,
                'files_changed': len(commit.files) if commit.files else 0,
                'additions': commit.stats.additions if commit.stats else 0,
                'deletions': commit.stats.deletions if commit.stats else 0
            })

        return recent_commits

    except Exception as e:
        print(f"Error getting recent commits: {e}")
        return []

def get_github_deployment_by_service_region(service: str, region: str = None, hours: int = 24) -> List[Dict[str, Any]]:
    """
    Get deployments filtered by service and optionally region.

    Args:
        service: Service name to filter by
        region: Region name to filter by (optional)
        hours: Number of hours to look back (default 24)

    Returns:
        List of deployment information dictionaries
    """
    try:
        # Get all recent deployments
        deployments = get_recent_github_deployments(hours=hours)

        # Filter by service and region
        filtered_deployments = []
        for deployment in deployments:
            # Check if service name is in environment, description, or ref
            environment = deployment.get('environment') or ''
            description = deployment.get('description') or ''
            ref = deployment.get('ref') or ''

            service_match = (
                service.lower() in environment.lower() or
                service.lower() in description.lower() or
                service.lower() in ref.lower()
            )

            if service_match:
                # If region is specified, check if it matches
                if region:
                    region_match = (
                        region.lower() in environment.lower() or
                        region.lower() in description.lower()
                    )
                    if region_match:
                        filtered_deployments.append(deployment)
                else:
                    filtered_deployments.append(deployment)

        return filtered_deployments

    except Exception as e:
        print(f"Error filtering deployments by service/region: {e}")
        return []

def analyze_github_deployment_correlation(incident_time: str, service: str = None, region: str = None) -> str:
    """
    Analyze potential correlation between incident and recent deployments.

    Args:
        incident_time: ISO format timestamp of incident
        service: Service name (optional)
        region: Region name (optional)

    Returns:
        Analysis report string
    """
    try:
        # Parse incident time
        incident_dt = datetime.fromisoformat(incident_time.replace('Z', '+00:00'))

        # Look back 6 hours from incident time
        hours_to_check = 6

        # Get recent activity
        prs = get_recent_github_merged_prs(hours=hours_to_check)
        deployments = get_recent_github_deployments(hours=hours_to_check)

        # Filter by service/region if provided
        if service:
            deployments = get_github_deployment_by_service_region(service, region, hours=hours_to_check)

        result = f"🔍 **Deployment Correlation Analysis**\n"
        result += f"Incident Time: {incident_time}\n"
        if service:
            result += f"Service: {service}\n"
        if region:
            result += f"Region: {region}\n\n"

        # Analyze deployments
        correlations = []
        for deployment in deployments:
            deploy_time = datetime.fromisoformat(deployment['created_at'].replace('Z', '+00:00'))
            time_diff = incident_dt - deploy_time

            if timedelta(0) <= time_diff <= timedelta(hours=6):
                correlation = {
                    'type': 'deployment',
                    'time_before_incident': str(time_diff),
                    'details': deployment
                }
                correlations.append(correlation)

        # Analyze PRs
        for pr in prs:
            pr_time = datetime.fromisoformat(pr['merged_at'].replace('Z', '+00:00'))
            time_diff = incident_dt - pr_time

            if timedelta(0) <= time_diff <= timedelta(hours=6):
                correlation = {
                    'type': 'pr',
                    'time_before_incident': str(time_diff),
                    'details': pr
                }
                correlations.append(correlation)

        # Generate report
        if correlations:
            result += f"⚠️ **Found {len(correlations)} potential correlations:**\n\n"

            for i, corr in enumerate(correlations, 1):
                if corr['type'] == 'deployment':
                    deploy = corr['details']
                    result += f"{i}. **Deployment** ({corr['time_before_incident']} before incident)\n"
                    result += f"   Environment: {deploy['environment']}\n"
                    result += f"   Status: {deploy['status']}\n"
                    result += f"   SHA: {deploy['sha'][:8]}\n"
                    result += f"   Time: {deploy['created_at']}\n\n"

                elif corr['type'] == 'pr':
                    pr = corr['details']
                    result += f"{i}. **Pull Request** ({corr['time_before_incident']} before incident)\n"
                    result += f"   #{pr['number']}: {pr['title']}\n"
                    result += f"   Author: {pr['author']}\n"
                    result += f"   Changes: +{pr['additions']} -{pr['deletions']}\n"
                    result += f"   Time: {pr['merged_at']}\n\n"
        else:
            result += "✅ **No correlations found** - No deployments or PRs in the 6 hours before the incident.\n"

        return result

    except Exception as e:
        return f"Error analyzing deployment correlation: {e}"


# Agent tool functions (these will be used by the AI agent)

def get_recent_github_activity(hours: int = 24) -> str:
    """Get recent GitHub activity including PRs, deployments, and commits."""
    try:
        prs = get_recent_github_merged_prs(hours=hours)
        deployments = get_recent_github_deployments(hours=hours)
        commits = get_recent_github_commits(hours=hours)

        result = f"Recent GitHub Activity (last {hours} hours):\n\n"

        # Recent PRs
        result += f"📥 **Merged Pull Requests ({len(prs)}):**\n"
        if prs:
            for pr in prs[:5]:  # Show top 5
                result += f"- #{pr['number']}: {pr['title']}\n"
                result += f"  Merged: {pr['merged_at']} by {pr['author']}\n"
                result += f"  Branch: {pr['branch']} → {pr['base_branch']}\n"
                result += f"  Changes: +{pr['additions']} -{pr['deletions']} ({pr['changed_files']} files)\n\n"
        else:
            result += "- No merged PRs found\n\n"

        # Recent Deployments
        result += f"🚀 **Deployments ({len(deployments)}):**\n"
        if deployments:
            for deploy in deployments[:5]:  # Show top 5
                result += f"- {deploy['environment']}: {deploy['ref']}\n"
                result += f"  Status: {deploy['status']}\n"
                result += f"  Created: {deploy['created_at']}\n"
                result += f"  SHA: {deploy['sha'][:8]}\n\n"
        else:
            result += "- No deployments found\n\n"

        # Recent Commits
        result += f"💻 **Commits ({len(commits)}):**\n"
        if commits:
            for commit in commits[:5]:  # Show top 5
                result += f"- {commit['sha'][:8]}: {commit['message'].split(chr(10))[0]}\n"
                result += f"  Author: {commit['author']}\n"
                result += f"  Time: {commit['committed_at']}\n\n"
        else:
            result += "- No commits found\n"

        return result

    except Exception as e:
        return f"Error retrieving GitHub activity: {e}"


def close_github_client():
    """Close the GitHub client."""
    global _github_client
    if _github_client:
        _github_client.close()
        _github_client = None
        print("GitHub client closed")