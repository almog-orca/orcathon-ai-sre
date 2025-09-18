#!/usr/bin/env python3

import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import requests

# Global client storage
_github_client = None
_github_org = None
_github_repo = None

def init_github_client(token: str, org: str = None, repo: str = None):
    """Initialize GitHub client for incident analysis"""
    global _github_client, _github_org, _github_repo
    _github_client = {
        'token': token,
        'headers': {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    }
    _github_org = org
    _github_repo = repo
    print(f"GitHub client initialized successfully for org: {org}")

def get_recent_github_merged_prs(hours: int = 24) -> List[Dict[str, Any]]:
    """Get recent merged PRs for incident correlation"""
    if not _github_client:
        return []

    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    url = f"https://api.github.com/repos/{_github_org}/{_github_repo}/pulls"

    try:
        response = requests.get(url, headers=_github_client['headers'], params={
            'state': 'closed',
            'sort': 'updated',
            'direction': 'desc',
            'per_page': 10
        })

        if response.status_code == 200:
            prs = response.json()
            recent_prs = []

            for pr in prs:
                if pr.get('merged_at'):
                    merged_time = datetime.fromisoformat(pr['merged_at'].replace('Z', '+00:00'))
                    if merged_time >= datetime.now(timezone.utc) - timedelta(hours=hours):
                        recent_prs.append({
                            'title': pr['title'],
                            'merged_at': pr['merged_at'],
                            'url': pr['html_url'],
                            'files_changed': pr.get('changed_files', 0),
                            'additions': pr.get('additions', 0),
                            'deletions': pr.get('deletions', 0)
                        })

            return recent_prs
    except Exception as e:
        print(f"Error fetching PRs: {e}")

    return []

def get_recent_github_deployments(hours: int = 24) -> List[Dict[str, Any]]:
    """Get recent deployments for incident correlation"""
    if not _github_client:
        return []

    url = f"https://api.github.com/repos/{_github_org}/{_github_repo}/deployments"

    try:
        response = requests.get(url, headers=_github_client['headers'], params={
            'per_page': 10
        })

        if response.status_code == 200:
            deployments = response.json()
            recent_deployments = []

            for deployment in deployments:
                created_time = datetime.fromisoformat(deployment['created_at'].replace('Z', '+00:00'))
                if created_time >= datetime.now(timezone.utc) - timedelta(hours=hours):
                    recent_deployments.append({
                        'environment': deployment.get('environment', 'unknown'),
                        'created_at': deployment['created_at'],
                        'ref': deployment.get('ref', 'unknown'),
                        'description': deployment.get('description', '')
                    })

            return recent_deployments
    except Exception as e:
        print(f"Error fetching deployments: {e}")

    return []

def analyze_github_deployment_correlation(incident_time: str, service: str = None, region: str = None) -> str:
    """Lightweight deployment correlation analysis"""
    try:
        # Parse incident time
        incident_dt = datetime.fromisoformat(incident_time.replace('Z', '+00:00'))

        # Look back 6 hours from incident time
        hours_to_check = 6

        # Get recent activity
        prs = get_recent_github_merged_prs(hours=hours_to_check)
        deployments = get_recent_github_deployments(hours=hours_to_check)

        result = f"🔍 **Deployment Correlation Analysis**\n"
        result += f"Incident Time: {incident_time}\n"
        if service:
            result += f"Service: {service}\n"
        if region:
            result += f"Region: {region}\n"

        result += f"\n**Recent PRs ({len(prs)} found):**\n"
        for pr in prs[:3]:  # Show top 3
            result += f"- {pr['title']} (merged: {pr['merged_at']}) - {pr['files_changed']} files\n"

        result += f"\n**Recent Deployments ({len(deployments)} found):**\n"
        for deployment in deployments[:3]:  # Show top 3
            result += f"- {deployment['environment']}: {deployment['ref']} ({deployment['created_at']})\n"

        # Simple correlation check
        correlation_found = len(prs) > 0 or len(deployments) > 0
        if correlation_found:
            result += f"\n⚠️ **Potential Correlation**: Found {len(prs)} PRs and {len(deployments)} deployments within {hours_to_check} hours of incident"
        else:
            result += f"\n✅ **No Correlation**: No recent GitHub activity found within {hours_to_check} hours of incident"

        return result

    except Exception as e:
        return f"❌ Error analyzing GitHub correlation: {str(e)}"