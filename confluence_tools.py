"""
Confluence tools for agno framework - search and retrieve wiki content.
Provides tools for searching pages, retrieving content, and finding documentation.
"""

import time
import json
import logging
import re
from typing import Optional, Dict, Any, List
from urllib.parse import quote, urljoin

import requests
from agno.tools import tool

logger = logging.getLogger("confluence_tools")


class ConfluenceAPIError(Exception):
    """Raised when a Confluence API call fails."""
    pass


class ConfluenceClient:
    """Confluence API client for making authenticated requests."""

    def __init__(self, base_url: str, token: str, email: str = None):
        """
        Initialize Confluence client.

        Args:
            base_url: Confluence base URL (e.g., https://company.atlassian.net/)
            token: Atlassian API token
            email: Email for basic auth (if needed)
        """
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/wiki/rest/api"
        self.token = token
        self.email = email

        # Try Bearer token first, fallback to basic auth if email provided
        if email:
            import base64
            auth_string = base64.b64encode(f"{email}:{token}".encode()).decode()
            self.headers = {
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        else:
            self.headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        self._space_cache = {}

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to Confluence API."""
        url = f"{self.api_base}/{endpoint.lstrip('/')}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Confluence API request failed: {e}")
            raise ConfluenceAPIError(f"API request failed: {e}")

    def search_content(self, query: str, limit: int = 25, spaces: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Search Confluence content using CQL (Confluence Query Language).

        Args:
            query: Search query text
            limit: Maximum number of results
            spaces: Optional list of space keys to search within

        Returns:
            List of search results with page info
        """
        # Build CQL query
        cql_parts = [f'text ~ "{query}"']
        if spaces:
            space_filter = " OR ".join([f'space = "{space}"' for space in spaces])
            cql_parts.append(f"({space_filter})")

        cql = " AND ".join(cql_parts)

        params = {
            "cql": cql,
            "limit": limit,
            "expand": "space,version,body.view"
        }

        try:
            result = self._make_request("GET", "content/search", params=params)
            return result.get("results", [])
        except ConfluenceAPIError as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_page_content(self, page_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full content of a Confluence page.

        Args:
            page_id: Confluence page ID

        Returns:
            Page content with metadata
        """
        params = {
            "expand": "body.view,space,version,ancestors"
        }

        try:
            return self._make_request("GET", f"content/{page_id}", params=params)
        except ConfluenceAPIError as e:
            logger.error(f"Failed to get page {page_id}: {e}")
            return None

    def search_by_title(self, title_query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search pages by title pattern.

        Args:
            title_query: Title search pattern
            limit: Maximum results

        Returns:
            List of matching pages
        """
        cql = f'title ~ "{title_query}"'
        params = {
            "cql": cql,
            "limit": limit,
            "expand": "space,version"
        }

        try:
            result = self._make_request("GET", "content/search", params=params)
            return result.get("results", [])
        except ConfluenceAPIError as e:
            logger.error(f"Title search failed: {e}")
            return []


# Global client instance
_confluence_client: Optional[ConfluenceClient] = None


def init_confluence_client(base_url: str, token: str, email: str = None) -> None:
    """Initialize the global Confluence client."""
    global _confluence_client
    _confluence_client = ConfluenceClient(base_url, token, email)


def get_confluence_client() -> ConfluenceClient:
    """Get the global Confluence client instance."""
    if _confluence_client is None:
        raise RuntimeError("Confluence client not initialized. Call init_confluence_client() first.")
    return _confluence_client


@tool
def search_confluence_content(query: str, limit: int = 10, spaces: Optional[str] = "OPR") -> List[Dict[str, Any]]:
    """
    Search SRE Operations (OPR) Confluence space for content matching the query.

    Args:
        query: Search terms to look for in SRE Operations wiki pages
        limit: Maximum number of results to return (default: 10)
        spaces: Space key to search within (default: "OPR" for SRE Operations)

    Returns:
        List of matching pages with title, URL, space, and excerpt from SRE Operations documentation
    """
    client = get_confluence_client()
    space_list = [s.strip() for s in spaces.split(",")] if spaces else None

    results = client.search_content(query, limit, space_list)

    formatted_results = []
    for result in results:
        # API returns data directly in result, not nested under result.content
        content = result
        space = content.get("space", {})

        space_key = space.get("key")
        space_display = f"SRE Operations ({space_key})" if space_key == "OPR" else space.get("name", space_key)

        formatted_results.append({
            "id": content.get("id"),
            "title": content.get("title", "Untitled"),
            "url": f"{client.base_url}/wiki{content.get('_links', {}).get('webui', '')}",
            "space": {
                "key": space.get("key"),
                "name": space.get("name"),
                "display": space_display
            },
            "type": content.get("type"),
            "lastModified": content.get("version", {}).get("when"),
            "excerpt": result.get("excerpt", ""),
            "team_context": "SRE Operations" if space_key == "OPR" else "Other"
        })

    return formatted_results


@tool
def get_confluence_page_content(page_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the full content of a specific Confluence page.

    Args:
        page_id: The Confluence page ID

    Returns:
        Page content including title, body, space info, and metadata
    """
    client = get_confluence_client()
    page = client.get_page_content(page_id)

    if not page:
        return None

    space = page.get("space", {})
    body = page.get("body", {}).get("view", {})

    return {
        "id": page.get("id"),
        "title": page.get("title"),
        "url": f"{client.base_url}/wiki{page.get('_links', {}).get('webui', '')}",
        "space": {
            "key": space.get("key"),
            "name": space.get("name")
        },
        "content": body.get("value", ""),
        "lastModified": page.get("version", {}).get("when"),
        "version": page.get("version", {}).get("number")
    }


@tool
def search_confluence_by_title(title_query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search Confluence pages by title pattern.

    Args:
        title_query: Title pattern to search for
        limit: Maximum number of results (default: 5)

    Returns:
        List of pages matching the title pattern
    """
    client = get_confluence_client()
    results = client.search_by_title(title_query, limit)

    formatted_results = []
    for result in results:
        # API returns data directly in result, not nested under result.content
        content = result
        space = content.get("space", {})

        formatted_results.append({
            "id": content.get("id"),
            "title": content.get("title", "Untitled"),
            "url": f"{client.base_url}/wiki{content.get('_links', {}).get('webui', '')}",
            "space": {
                "key": space.get("key"),
                "name": space.get("name")
            },
            "type": content.get("type"),
            "lastModified": content.get("version", {}).get("when")
        })

    return formatted_results