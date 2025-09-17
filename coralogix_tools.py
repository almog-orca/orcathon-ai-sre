"""
Coralogix tools for agno framework - query and retrieve logs using Lucene syntax.
Provides tools for searching logs, filtering by timeframe, and analyzing log data.
"""

import os
import time
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
from urllib.parse import quote

import requests
from agno.tools import tool

logger = logging.getLogger("coralogix_tools")


class CoralogixAPIError(Exception):
    """Raised when a Coralogix API call fails."""
    pass


class CoralogixClient:
    """Coralogix API client for making authenticated requests."""

    def __init__(self, api_key: str, base_url: str = "https://api.coralogix.com"):
        """
        Initialize Coralogix client.

        Args:
            api_key: Coralogix API key with DataQuerying permissions
            base_url: Coralogix API base URL (default: https://api.coralogix.com)
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        
        # OpenSearch API endpoint for log queries
        self.query_endpoint = f"{self.base_url}/data/os-api/*/_search"
        
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _make_request(self, method: str, url: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to Coralogix API."""
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                params=params,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Coralogix API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    logger.error(f"Error details: {error_details}")
                except:
                    logger.error(f"Response text: {e.response.text}")
            raise CoralogixAPIError(f"API request failed: {e}")

    def query_logs(
        self, 
        lucene_query: str, 
        start_time: str, 
        end_time: str,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Query logs using Lucene syntax within a specified timeframe.

        Args:
            lucene_query: Lucene query string (e.g., "level:ERROR AND service:auth")
            start_time: Start time in ISO 8601 format (e.g., "2023-12-01T00:00:00Z")
            end_time: End time in ISO 8601 format (e.g., "2023-12-01T23:59:59Z")
            limit: Maximum number of logs to return (default: 100)
            offset: Number of logs to skip for pagination (default: 0)

        Returns:
            Dictionary containing query results with logs and metadata
        """
        # OpenSearch/Elasticsearch query structure with Lucene syntax
        data = {
            "query": {
                "bool": {
                    "filter": [
                        {
                            "query_string": {
                                "query": lucene_query
                            }
                        },
                        {
                            "range": {
                                "coralogix.timestamp": {
                                    "gte": start_time,
                                    "lt": end_time
                                }
                            }
                        }
                    ]
                }
            },
            "from": offset,
            "size": limit,
            "sort": [
                {
                    "coralogix.timestamp": {
                        "order": "desc"
                    }
                }
            ]
        }

        try:
            result = self._make_request("POST", self.query_endpoint, data=data)
            # Transform OpenSearch response to our expected format
            hits = result.get("hits", {}).get("hits", [])
            logs = [hit.get("_source", {}) for hit in hits]
            return {"logs": logs, "total": result.get("hits", {}).get("total", {}).get("value", 0)}
        except CoralogixAPIError as e:
            logger.error(f"Log query failed: {e}")
            return {"logs": [], "error": str(e)}

    def query_logs_last_hours(
        self, 
        lucene_query: str, 
        hours: int = 24,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Query logs from the last N hours using Lucene syntax.

        Args:
            lucene_query: Lucene query string
            hours: Number of hours to look back (default: 24)
            limit: Maximum number of logs to return (default: 100)

        Returns:
            Dictionary containing query results with logs and metadata
        """
        # Use OpenSearch relative time format for better performance
        start_time = f"now-{hours}h"
        end_time = "now"
        
        return self.query_logs(lucene_query, start_time, end_time, limit)

    def query_logs_last_minutes(
        self, 
        lucene_query: str, 
        minutes: int = 60,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Query logs from the last N minutes using Lucene syntax.

        Args:
            lucene_query: Lucene query string
            minutes: Number of minutes to look back (default: 60)
            limit: Maximum number of logs to return (default: 100)

        Returns:
            Dictionary containing query results with logs and metadata
        """
        # Use OpenSearch relative time format for better performance
        start_time = f"now-{minutes}m"
        end_time = "now"
        
        return self.query_logs(lucene_query, start_time, end_time, limit)


# Global client instance
_coralogix_client: Optional[CoralogixClient] = None


def init_coralogix_client(api_key: str, base_url: str = "https://api.coralogix.com") -> None:
    """Initialize the global Coralogix client."""
    global _coralogix_client
    _coralogix_client = CoralogixClient(api_key, base_url)


def get_coralogix_client() -> CoralogixClient:
    """Get the global Coralogix client instance."""
    if _coralogix_client is None:
        raise RuntimeError("Coralogix client not initialized. Call init_coralogix_client() first.")
    return _coralogix_client


def _format_log_results(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Format raw Coralogix API results for better readability."""
    if "error" in results:
        return [{"error": results["error"]}]
    
    logs = results.get("logs", [])
    formatted_logs = []
    
    for log in logs:
        formatted_log = {
            "timestamp": log.get("timestamp"),
            "level": log.get("level", log.get("severity")),
            "message": log.get("message", log.get("text")),
            "source": log.get("source", log.get("application")),
            "subsystem": log.get("subsystem"),
            "computer": log.get("computer", log.get("host")),
            "raw_log": log  # Keep original for detailed analysis
        }
        
        # Clean up None values
        formatted_log = {k: v for k, v in formatted_log.items() if v is not None}
        formatted_logs.append(formatted_log)
    
    return formatted_logs


@tool
def query_coralogix_logs(
    lucene_query: str, 
    start_time: str, 
    end_time: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Query Coralogix logs using Lucene syntax within a specific timeframe.
    
    Use this for custom time ranges when you need logs from a specific period.

    Args:
        lucene_query: Lucene query string. Examples:
            - "level:ERROR" (all error logs)
            - "service:auth-service AND level:ERROR" (error logs from auth service)
            - "message:*timeout*" (logs containing "timeout")
            - "source:kubernetes AND NOT level:DEBUG" (non-debug k8s logs)
        start_time: Start time in ISO 8601 format (e.g., "2023-12-01T00:00:00Z")
        end_time: End time in ISO 8601 format (e.g., "2023-12-01T23:59:59Z")
        limit: Maximum number of logs to return (default: 50, max recommended: 1000)

    Returns:
        List of formatted log entries with timestamp, level, message, source, and metadata
    """
    client = get_coralogix_client()
    results = client.query_logs(lucene_query, start_time, end_time, limit)
    return _format_log_results(results)


@tool
def query_coralogix_logs_last_24h(
    lucene_query: str = "*",
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Query Coralogix logs from the last 24 hours using Lucene syntax.
    
    Perfect for getting recent logs when investigating current issues.

    Args:
        lucene_query: Lucene query string (default: "*" for all logs). Examples:
            - "*" (all logs from last 24h)
            - "level:ERROR OR level:WARN" (errors and warnings)
            - "service:payment-service" (logs from payment service)
            - "message:*exception* OR message:*error*" (logs with exception/error keywords)
        limit: Maximum number of logs to return (default: 50)

    Returns:
        List of formatted log entries from the last 24 hours
    """
    client = get_coralogix_client()
    results = client.query_logs_last_hours(lucene_query, hours=24, limit=limit)
    return _format_log_results(results)


@tool
def query_coralogix_logs_last_hour(
    lucene_query: str = "*",
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Query Coralogix logs from the last hour using Lucene syntax.
    
    Great for immediate troubleshooting and checking recent activity.

    Args:
        lucene_query: Lucene query string (default: "*" for all logs). Examples:
            - "level:ERROR" (recent errors)
            - "source:nginx AND level:WARN" (nginx warnings)
            - "message:*failed* AND service:api" (API failures)
        limit: Maximum number of logs to return (default: 100)

    Returns:
        List of formatted log entries from the last hour
    """
    client = get_coralogix_client()
    results = client.query_logs_last_minutes(lucene_query, minutes=60, limit=limit)
    return _format_log_results(results)


@tool
def query_coralogix_logs_custom_hours(
    lucene_query: str,
    hours: int,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Query Coralogix logs from the last N hours using Lucene syntax.
    
    Flexible time range for when you need logs from a specific number of hours back.

    Args:
        lucene_query: Lucene query string. Examples:
            - "level:ERROR AND service:database" (database errors)
            - "message:*deployment* AND level:INFO" (deployment info logs)
            - "source:application AND NOT message:*health*" (app logs excluding health checks)
        hours: Number of hours to look back (e.g., 2, 6, 12, 48)
        limit: Maximum number of logs to return (default: 50)

    Returns:
        List of formatted log entries from the last N hours
    """
    client = get_coralogix_client()
    results = client.query_logs_last_hours(lucene_query, hours=hours, limit=limit)
    return _format_log_results(results)


@tool
def query_coralogix_error_logs_24h(
    service_filter: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Query ERROR level logs from the last 24 hours, optionally filtered by service.
    
    Specialized function for error analysis and incident investigation.

    Args:
        service_filter: Optional service name to filter by (e.g., "auth-service", "payment-api")
        limit: Maximum number of logs to return (default: 50)

    Returns:
        List of ERROR level log entries from the last 24 hours
    """
    if service_filter:
        lucene_query = f"level:ERROR AND (service:{service_filter} OR source:{service_filter} OR application:{service_filter})"
    else:
        lucene_query = "level:ERROR"
    
    client = get_coralogix_client()
    results = client.query_logs_last_hours(lucene_query, hours=24, limit=limit)
    return _format_log_results(results)


@tool
def query_coralogix_logs_by_service(
    service_name: str,
    hours: int = 24,
    log_level: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Query logs from a specific service, optionally filtered by log level.
    
    Perfect for service-specific troubleshooting and monitoring.

    Args:
        service_name: Name of the service to filter by
        hours: Number of hours to look back (default: 24)
        log_level: Optional log level filter (ERROR, WARN, INFO, DEBUG)
        limit: Maximum number of logs to return (default: 50)

    Returns:
        List of log entries from the specified service
    """
    # Build query to match service in multiple possible fields
    service_query = f"(service:{service_name} OR source:{service_name} OR application:{service_name})"
    
    if log_level:
        lucene_query = f"{service_query} AND level:{log_level.upper()}"
    else:
        lucene_query = service_query
    
    client = get_coralogix_client()
    results = client.query_logs_last_hours(lucene_query, hours=hours, limit=limit)
    return _format_log_results(results)


# Helper function to generate common Lucene query examples
def get_lucene_query_examples() -> Dict[str, str]:
    """
    Get common Lucene query examples for reference.
    
    Returns:
        Dictionary of query examples with descriptions
    """
    return {
        "all_errors": "level:ERROR",
        "specific_service_errors": "level:ERROR AND service:auth-service",
        "timeout_issues": "message:*timeout* OR message:*timed*out*",
        "database_errors": "(service:database OR source:postgres OR source:mysql) AND level:ERROR",
        "kubernetes_warnings": "source:kubernetes AND level:WARN",
        "api_failures": "message:*failed* AND (service:api OR source:api)",
        "exclude_health_checks": "NOT message:*health* AND NOT message:*ping*",
        "high_severity": "level:ERROR OR level:FATAL OR level:CRITICAL",
        "recent_deployments": "message:*deploy* OR message:*release*",
        "authentication_issues": "message:*auth* OR message:*login* OR message:*token*"
    }