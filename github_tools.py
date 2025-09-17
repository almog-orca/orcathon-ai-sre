import os
import re
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

# Code Analysis Helper Functions

def analyze_file_diff(filename: str, patch: str) -> Dict[str, Any]:
    """
    Analyze a file diff to extract meaningful code changes.

    Args:
        filename: Name of the file
        patch: Git patch content

    Returns:
        Dictionary containing analysis of the changes
    """
    if not patch:
        return {
            'filename': filename,
            'file_type': get_file_type(filename),
            'changes': {},
            'risk_level': 'low'
        }

    file_type = get_file_type(filename)
    changes = {
        'lines_added': [],
        'lines_removed': [],
        'functions_added': [],
        'functions_modified': [],
        'imports_added': [],
        'imports_removed': [],
        'config_changes': [],
        'critical_patterns': []
    }

    lines = patch.split('\n')
    current_line_num = 0

    for line in lines:
        if line.startswith('@@'):
            # Extract line number from hunk header
            match = re.search(r'\+(\d+)', line)
            if match:
                current_line_num = int(match.group(1))
        elif line.startswith('+') and not line.startswith('+++'):
            # Added line
            added_line = line[1:]
            changes['lines_added'].append({
                'line_num': current_line_num,
                'content': added_line
            })

            # Analyze added content
            analyze_line_content(added_line, changes, 'added', file_type)
            current_line_num += 1

        elif line.startswith('-') and not line.startswith('---'):
            # Removed line
            removed_line = line[1:]
            changes['lines_removed'].append({
                'line_num': current_line_num,
                'content': removed_line
            })

            # Analyze removed content
            analyze_line_content(removed_line, changes, 'removed', file_type)

        elif not line.startswith('\\'):
            # Unchanged line
            current_line_num += 1

    # Determine risk level
    risk_level = assess_change_risk(changes, file_type, filename)

    return {
        'filename': filename,
        'file_type': file_type,
        'changes': changes,
        'risk_level': risk_level,
        'summary': generate_change_summary(changes, file_type)
    }

def get_file_type(filename: str) -> str:
    """Determine file type based on extension."""
    ext = filename.split('.')[-1].lower() if '.' in filename else ''

    type_mapping = {
        'py': 'python',
        'js': 'javascript',
        'ts': 'typescript',
        'jsx': 'react',
        'tsx': 'react',
        'java': 'java',
        'go': 'go',
        'rs': 'rust',
        'cpp': 'cpp',
        'c': 'c',
        'yml': 'yaml',
        'yaml': 'yaml',
        'json': 'json',
        'xml': 'xml',
        'sql': 'sql',
        'sh': 'shell',
        'dockerfile': 'docker',
        'tf': 'terraform',
        'md': 'markdown'
    }

    if 'dockerfile' in filename.lower():
        return 'docker'
    elif filename.lower() in ['makefile', 'makefile.am', 'makefile.in']:
        return 'makefile'
    elif filename.lower() in ['requirements.txt', 'package.json', 'cargo.toml', 'pom.xml']:
        return 'dependency'
    elif 'config' in filename.lower() or ext in ['conf', 'cfg', 'ini', 'env']:
        return 'config'

    return type_mapping.get(ext, 'unknown')

def analyze_line_content(line: str, changes: Dict, change_type: str, file_type: str):
    """Analyze a single line of code for important patterns."""
    line_stripped = line.strip()

    # Function definitions
    if file_type == 'python':
        if re.match(r'def\s+\w+\s*\(', line_stripped):
            func_name = re.search(r'def\s+(\w+)', line_stripped)
            if func_name:
                key = f'functions_{change_type}'
                if key in changes:
                    changes[key].append(func_name.group(1))

        # Import statements
        if line_stripped.startswith('import ') or line_stripped.startswith('from '):
            key = f'imports_{change_type}'
            if key in changes:
                changes[key].append(line_stripped)

    elif file_type in ['javascript', 'typescript']:
        # Function definitions
        if re.match(r'(function\s+\w+|const\s+\w+\s*=.*=>|\w+\s*:\s*function)', line_stripped):
            key = f'functions_{change_type}'
            if key in changes:
                changes[key].append(line_stripped[:50] + '...' if len(line_stripped) > 50 else line_stripped)

        # Import statements
        if line_stripped.startswith('import ') or line_stripped.startswith('require('):
            key = f'imports_{change_type}'
            if key in changes:
                changes[key].append(line_stripped)

    # Critical patterns (all languages)
    critical_patterns = [
        r'\b(password|secret|key|token)\b',
        r'\b(delete|drop|truncate)\b',
        r'\b(sudo|chmod|chown)\b',
        r'\b(eval|exec|system)\b',
        r'(http|https)://.*',
        r'\b(localhost|127\.0\.0\.1)\b'
    ]

    for pattern in critical_patterns:
        if re.search(pattern, line_stripped, re.IGNORECASE):
            changes['critical_patterns'].append({
                'pattern': pattern,
                'line': line_stripped,
                'type': change_type
            })

    # Configuration changes
    if file_type in ['yaml', 'json', 'config'] or 'config' in changes:
        changes['config_changes'].append({
            'type': change_type,
            'content': line_stripped
        })

def assess_change_risk(changes: Dict, file_type: str, filename: str) -> str:
    """Assess the risk level of changes."""
    risk_score = 0

    # High risk file types
    if file_type in ['config', 'yaml', 'json', 'docker', 'terraform']:
        risk_score += 2

    # High risk filenames
    high_risk_files = ['dockerfile', 'docker-compose', 'requirements.txt', 'package.json',
                      'makefile', '.env', 'config', 'settings']
    if any(risk_file in filename.lower() for risk_file in high_risk_files):
        risk_score += 2

    # Function changes
    if changes.get('functions_added') or changes.get('functions_modified'):
        risk_score += 1

    # Import changes
    if changes.get('imports_added') or changes.get('imports_removed'):
        risk_score += 1

    # Critical patterns
    if changes.get('critical_patterns'):
        risk_score += 3

    # Configuration changes
    if changes.get('config_changes'):
        risk_score += 2

    if risk_score >= 5:
        return 'high'
    elif risk_score >= 3:
        return 'medium'
    else:
        return 'low'

def generate_change_summary(changes: Dict, file_type: str = None) -> str:
    """Generate a human-readable summary of changes."""
    summary_parts = []

    if changes.get('functions_added'):
        summary_parts.append(f"Added {len(changes['functions_added'])} functions")

    if changes.get('functions_modified'):
        summary_parts.append(f"Modified {len(changes['functions_modified'])} functions")

    if changes.get('imports_added'):
        summary_parts.append(f"Added {len(changes['imports_added'])} imports")

    if changes.get('imports_removed'):
        summary_parts.append(f"Removed {len(changes['imports_removed'])} imports")

    if changes.get('config_changes'):
        summary_parts.append(f"Modified configuration ({len(changes['config_changes'])} changes)")

    if changes.get('critical_patterns'):
        summary_parts.append(f"⚠️ Contains {len(changes['critical_patterns'])} critical patterns")

    lines_added = len(changes.get('lines_added', []))
    lines_removed = len(changes.get('lines_removed', []))

    if lines_added or lines_removed:
        summary_parts.append(f"+{lines_added} -{lines_removed} lines")

    return '; '.join(summary_parts) if summary_parts else 'No significant changes detected'

def calculate_pr_risk(file_analyses: List[Dict[str, Any]]) -> str:
    """Calculate overall risk level for a PR based on file analyses."""
    if not file_analyses:
        return 'low'

    risk_scores = {'low': 1, 'medium': 3, 'high': 5}
    total_score = sum(risk_scores.get(analysis.get('risk_level', 'low'), 1) for analysis in file_analyses)
    avg_score = total_score / len(file_analyses)

    if avg_score >= 4:
        return 'high'
    elif avg_score >= 2:
        return 'medium'
    else:
        return 'low'

def generate_pr_summary(file_analyses: List[Dict[str, Any]]) -> str:
    """Generate a summary of changes across all files in a PR."""
    if not file_analyses:
        return 'No file analysis available'

    summary_parts = []

    # Count file types
    file_types = {}
    high_risk_files = 0
    total_functions_changed = 0
    total_imports_changed = 0
    config_files_changed = 0
    critical_patterns_found = 0

    for analysis in file_analyses:
        file_type = analysis.get('file_type', 'unknown')
        file_types[file_type] = file_types.get(file_type, 0) + 1

        if analysis.get('risk_level') == 'high':
            high_risk_files += 1

        changes = analysis.get('changes', {})
        total_functions_changed += len(changes.get('functions_added', [])) + len(changes.get('functions_modified', []))
        total_imports_changed += len(changes.get('imports_added', [])) + len(changes.get('imports_removed', []))

        if analysis.get('file_type') in ['config', 'yaml', 'json'] or 'config' in analysis.get('filename', '').lower():
            config_files_changed += 1

        critical_patterns_found += len(changes.get('critical_patterns', []))

    # Generate summary
    summary_parts.append(f"{len(file_analyses)} files changed")

    if file_types:
        top_types = sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:3]
        types_str = ', '.join([f"{count} {ftype}" for ftype, count in top_types])
        summary_parts.append(f"Types: {types_str}")

    if high_risk_files:
        summary_parts.append(f"⚠️ {high_risk_files} high-risk files")

    if total_functions_changed:
        summary_parts.append(f"{total_functions_changed} functions changed")

    if total_imports_changed:
        summary_parts.append(f"{total_imports_changed} imports changed")

    if config_files_changed:
        summary_parts.append(f"{config_files_changed} config files")

    if critical_patterns_found:
        summary_parts.append(f"🚨 {critical_patterns_found} critical patterns")

    return '; '.join(summary_parts)

def calculate_code_quality_metrics(file_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate code quality metrics from file analyses.

    Returns:
        Dictionary containing various code quality metrics
    """
    metrics = {
        'complexity_score': 0,
        'maintainability_score': 0,
        'security_risk_score': 0,
        'test_coverage_impact': 'unknown',
        'documentation_impact': 'none',
        'dependency_risk': 'low',
        'breaking_change_risk': 'low',
        'performance_impact': 'low'
    }

    if not file_analyses:
        return metrics

    total_files = len(file_analyses)
    complexity_factors = 0
    security_issues = 0
    config_changes = 0
    test_files = 0
    doc_files = 0
    dependency_files = 0
    breaking_changes = 0

    for analysis in file_analyses:
        filename = analysis.get('filename', '')
        file_type = analysis.get('file_type', 'unknown')
        changes = analysis.get('changes', {})

        # Complexity factors
        if changes.get('functions_added') or changes.get('functions_modified'):
            complexity_factors += len(changes.get('functions_added', [])) + len(changes.get('functions_modified', []))

        if changes.get('imports_added') or changes.get('imports_removed'):
            complexity_factors += len(changes.get('imports_added', [])) + len(changes.get('imports_removed', []))

        # Security issues
        security_issues += len(changes.get('critical_patterns', []))

        # Configuration changes
        if file_type in ['config', 'yaml', 'json'] or 'config' in filename.lower():
            config_changes += 1

        # Test files
        if 'test' in filename.lower() or file_type in ['test', 'spec']:
            test_files += 1

        # Documentation files
        if file_type == 'markdown' or 'readme' in filename.lower() or 'doc' in filename.lower():
            doc_files += 1

        # Dependency files
        if file_type == 'dependency':
            dependency_files += 1

        # Breaking changes (function removals, major config changes)
        if changes.get('functions_removed') or (file_type in ['config', 'yaml'] and analysis.get('risk_level') == 'high'):
            breaking_changes += 1

    # Calculate scores (0-100 scale)

    # Complexity Score (higher = more complex)
    complexity_per_file = complexity_factors / total_files if total_files > 0 else 0
    metrics['complexity_score'] = min(100, int(complexity_per_file * 20))

    # Maintainability Score (higher = better maintainability)
    maintainability = 100
    if complexity_per_file > 3:
        maintainability -= 30
    if security_issues > 0:
        maintainability -= 20
    if config_changes > total_files * 0.3:  # More than 30% config files
        maintainability -= 15
    metrics['maintainability_score'] = max(0, maintainability)

    # Security Risk Score (higher = more risky)
    security_per_file = security_issues / total_files if total_files > 0 else 0
    metrics['security_risk_score'] = min(100, int(security_per_file * 50))

    # Test Coverage Impact
    if test_files > 0:
        test_ratio = test_files / total_files
        if test_ratio >= 0.3:
            metrics['test_coverage_impact'] = 'improved'
        elif test_ratio >= 0.1:
            metrics['test_coverage_impact'] = 'maintained'
        else:
            metrics['test_coverage_impact'] = 'minimal'
    else:
        metrics['test_coverage_impact'] = 'none'

    # Documentation Impact
    if doc_files > 0:
        metrics['documentation_impact'] = 'updated'
    else:
        metrics['documentation_impact'] = 'none'

    # Dependency Risk
    if dependency_files > 0:
        metrics['dependency_risk'] = 'high' if dependency_files > 2 else 'medium'
    else:
        metrics['dependency_risk'] = 'low'

    # Breaking Change Risk
    if breaking_changes > 0:
        metrics['breaking_change_risk'] = 'high' if breaking_changes > 2 else 'medium'
    else:
        metrics['breaking_change_risk'] = 'low'

    # Performance Impact (based on file types and changes)
    perf_impact_files = sum(1 for analysis in file_analyses
                           if analysis.get('file_type') in ['config', 'sql', 'docker']
                           or 'performance' in analysis.get('filename', '').lower()
                           or 'cache' in analysis.get('filename', '').lower())

    if perf_impact_files > total_files * 0.2:  # More than 20% performance-related files
        metrics['performance_impact'] = 'high'
    elif perf_impact_files > 0:
        metrics['performance_impact'] = 'medium'
    else:
        metrics['performance_impact'] = 'low'

    return metrics

def generate_quality_report(metrics: Dict[str, Any]) -> str:
    """Generate a human-readable quality report."""
    report_parts = []

    # Complexity
    complexity = metrics.get('complexity_score', 0)
    if complexity >= 70:
        report_parts.append(f"🔴 High complexity ({complexity}/100)")
    elif complexity >= 40:
        report_parts.append(f"🟡 Medium complexity ({complexity}/100)")
    else:
        report_parts.append(f"🟢 Low complexity ({complexity}/100)")

    # Maintainability
    maintainability = metrics.get('maintainability_score', 100)
    if maintainability >= 80:
        report_parts.append(f"🟢 Good maintainability ({maintainability}/100)")
    elif maintainability >= 60:
        report_parts.append(f"🟡 Fair maintainability ({maintainability}/100)")
    else:
        report_parts.append(f"🔴 Poor maintainability ({maintainability}/100)")

    # Security
    security = metrics.get('security_risk_score', 0)
    if security >= 50:
        report_parts.append(f"🚨 High security risk ({security}/100)")
    elif security >= 20:
        report_parts.append(f"⚠️ Medium security risk ({security}/100)")
    else:
        report_parts.append(f"✅ Low security risk ({security}/100)")

    # Other metrics
    test_impact = metrics.get('test_coverage_impact', 'unknown')
    if test_impact != 'none':
        report_parts.append(f"Tests: {test_impact}")

    dep_risk = metrics.get('dependency_risk', 'low')
    if dep_risk != 'low':
        report_parts.append(f"Dependencies: {dep_risk} risk")

    breaking_risk = metrics.get('breaking_change_risk', 'low')
    if breaking_risk != 'low':
        report_parts.append(f"Breaking changes: {breaking_risk} risk")

    perf_impact = metrics.get('performance_impact', 'low')
    if perf_impact != 'low':
        report_parts.append(f"Performance impact: {perf_impact}")

    return ' | '.join(report_parts)

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
                # Get detailed file changes with actual diffs
                file_analyses = []
                try:
                    files = pr.get_files()
                    for file in files:
                        file_analysis = analyze_file_diff(file.filename, file.patch)
                        file_analysis.update({
                            'status': file.status,  # 'added', 'removed', 'modified', 'renamed'
                            'additions': file.additions,
                            'deletions': file.deletions,
                            'total_changes': file.changes,  # This is an integer
                            'blob_url': file.blob_url,
                            'raw_url': file.raw_url
                        })
                        file_analyses.append(file_analysis)
                except Exception as e:
                    print(f"Warning: Could not fetch file details for PR #{pr.number}: {e}")

                # Calculate overall risk assessment and quality metrics
                overall_risk = calculate_pr_risk(file_analyses)
                quality_metrics = calculate_code_quality_metrics(file_analyses)

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
                    'labels': [label.name for label in pr.labels],
                    'file_analyses': file_analyses,
                    'overall_risk': overall_risk,
                    'change_summary': generate_pr_summary(file_analyses),
                    'quality_metrics': quality_metrics,
                    'quality_report': generate_quality_report(quality_metrics)
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

def get_recent_github_commits(hours: int = 24, repo: str = None, branch: str = None) -> List[Dict[str, Any]]:
    """
    Get recent commits to a repository.

    Args:
        hours: Number of hours to look back (default 24)
        repo: Repository name (format: "owner/repo", optional)
        branch: Branch name to check (default: auto-detect default branch)

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

        # Determine branch to use
        if not branch:
            try:
                # Try to get the default branch
                branch = repository.default_branch
                print(f"Using default branch: {branch}")
            except Exception as e:
                print(f"Warning: Could not get default branch: {e}")
                # Try common branch names
                for common_branch in ['main', 'master', 'develop']:
                    try:
                        repository.get_branch(common_branch)
                        branch = common_branch
                        print(f"Using branch: {branch}")
                        break
                    except:
                        continue
                else:
                    print("Could not find a valid branch")
                    return []

        # Get recent commits
        try:
            commits = repository.get_commits(sha=branch, since=since_time)
        except Exception as e:
            print(f"Error getting commits from branch '{branch}': {e}")
            # Try without specifying branch (gets default)
            try:
                commits = repository.get_commits(since=since_time)
                print("Successfully retrieved commits using default branch")
            except Exception as e2:
                print(f"Error getting commits without branch specification: {e2}")
                return []

        recent_commits = []
        commit_count = 0
        max_commits = 10  # Limit to prevent timeout

        for commit in commits:
            commit_count += 1
            print(f"Processing commit {commit_count}/{max_commits}: {commit.sha[:8]}")
            if commit_count > max_commits:
                print(f"Limiting to first {max_commits} commits to prevent timeout")
                break
            # Get detailed file changes with actual diffs
            file_analyses = []
            try:
                if commit.files:
                    file_list = list(commit.files)[:3]  # Limit to first 3 files per commit
                    for file in file_list:
                        file_analysis = analyze_file_diff(file.filename, file.patch)
                        file_analysis.update({
                            'status': file.status,  # 'added', 'removed', 'modified', 'renamed'
                            'additions': file.additions,
                            'deletions': file.deletions,
                            'total_changes': file.changes,  # This is an integer
                            'blob_url': file.blob_url,
                            'raw_url': file.raw_url
                        })
                        file_analyses.append(file_analysis)
            except Exception as e:
                print(f"Warning: Could not fetch file details for commit {commit.sha[:8]}: {e}")

            # Calculate overall risk assessment and quality metrics
            overall_risk = calculate_pr_risk(file_analyses)  # Reuse the same logic
            quality_metrics = calculate_code_quality_metrics(file_analyses)

            recent_commits.append({
                'sha': commit.sha,
                'message': commit.commit.message,
                'author': commit.commit.author.name,
                'author_email': commit.commit.author.email,
                'committer': commit.commit.committer.name,
                'committed_at': commit.commit.committer.date.isoformat(),
                'url': commit.html_url,
                'files_changed': len(list(commit.files)) if commit.files else 0,
                'additions': commit.stats.additions if commit.stats else 0,
                'deletions': commit.stats.deletions if commit.stats else 0,
                'file_analyses': file_analyses,
                'overall_risk': overall_risk,
                'change_summary': generate_pr_summary(file_analyses),  # Reuse the same logic
                'quality_metrics': quality_metrics,
                'quality_report': generate_quality_report(quality_metrics)
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
                    result += f"   Risk Level: {pr.get('overall_risk', 'unknown')}\n"

                    # Add detailed change analysis
                    if pr.get('change_summary'):
                        result += f"   Change Summary: {pr['change_summary']}\n"

                    if pr.get('quality_report'):
                        result += f"   Quality: {pr['quality_report']}\n"

                    # Highlight critical changes
                    if pr.get('file_analyses'):
                        critical_files = [f for f in pr['file_analyses'] if f.get('risk_level') == 'high']
                        if critical_files:
                            result += f"   🚨 High-Risk Files: {', '.join([f.get('filename', 'unknown') for f in critical_files[:3]])}\n"

                        # Show functions and config changes
                        all_functions = []
                        config_changes = []
                        for file_analysis in pr['file_analyses']:
                            changes = file_analysis.get('changes', {})
                            all_functions.extend(changes.get('functions_added', []))
                            all_functions.extend(changes.get('functions_modified', []))
                            if file_analysis.get('file_type') in ['config', 'yaml', 'json']:
                                config_changes.append(file_analysis.get('filename', 'unknown'))

                        if all_functions:
                            result += f"   🔧 Functions Changed: {', '.join(all_functions[:5])}\n"
                        if config_changes:
                            result += f"   ⚙️ Config Files: {', '.join(config_changes)}\n"

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
                result += f"  Changes: +{pr['additions']} -{pr['deletions']} ({pr['changed_files']} files)\n"
                result += f"  Risk: {pr.get('overall_risk', 'unknown')}\n"

                if pr.get('change_summary'):
                    result += f"  Summary: {pr['change_summary']}\n"

                if pr.get('quality_metrics'):
                    quality = pr['quality_metrics']
                    if quality.get('security_risk_score', 0) > 20:
                        result += f"  ⚠️ Security Risk: {quality['security_risk_score']}/100\n"
                    if quality.get('breaking_change_risk', 'low') != 'low':
                        result += f"  💥 Breaking Change Risk: {quality['breaking_change_risk']}\n"

                result += "\n"
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
                result += f"  Time: {commit['committed_at']}\n"
                result += f"  Risk: {commit.get('overall_risk', 'unknown')}\n"

                if commit.get('change_summary'):
                    result += f"  Summary: {commit['change_summary']}\n"

                if commit.get('quality_metrics'):
                    quality = commit['quality_metrics']
                    if quality.get('security_risk_score', 0) > 20:
                        result += f"  ⚠️ Security Risk: {quality['security_risk_score']}/100\n"
                    if quality.get('breaking_change_risk', 'low') != 'low':
                        result += f"  💥 Breaking Change Risk: {quality['breaking_change_risk']}\n"

                result += "\n"
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