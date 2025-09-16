#!/usr/bin/env python3
"""
Debug script to test Confluence API connectivity and search functionality.
"""

import dotenv
import os
import json
from confluence_tools import init_confluence_client, get_confluence_client

dotenv.load_dotenv()

def test_confluence_api():
    """Test Confluence API with various approaches"""

    # Initialize client
    base_url = os.getenv("CONFLUENCE_BASE_URL")
    token = os.getenv("CONFLUENCE_TOKEN")
    email = os.getenv("CONFLUENCE_EMAIL")

    print(f"Base URL: {base_url}")
    print(f"Token: {'*' * (len(token) - 4) + token[-4:] if token else 'None'}")
    print(f"Email: {email}")
    print()

    init_confluence_client(base_url, token, email)
    client = get_confluence_client()

    print(f"API Base: {client.api_base}")
    print()

    # Test 1: Try to get the specific page we know exists
    print("=== Test 1: Get specific page (3278536757) ===")
    try:
        page = client.get_page_content("3278536757")
        if page:
            print(f"✅ Found page: {page.get('title')}")
            print(f"   Space: {page.get('space', {}).get('key')}")
            print(f"   ID: {page.get('id')}")
        else:
            print("❌ Page not found or no access")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    # Test 2: Search without space filter
    print("=== Test 2: Search all spaces for 'skip by tag' ===")
    try:
        results = client.search_content("skip by tag", limit=5, spaces=None)
        print(f"Found {len(results)} results")
        for i, result in enumerate(results, 1):
            content = result.get("content", {})
            space = content.get("space", {})
            print(f"{i}. {content.get('title', 'No title')}")
            print(f"   Space: {space.get('key', 'No key')} - {space.get('name', 'No name')}")
            print(f"   ID: {content.get('id', 'No ID')}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    # Test 3: Search OPR space specifically
    print("=== Test 3: Search OPR space for 'skip by tag' ===")
    try:
        results = client.search_content("skip by tag", limit=5, spaces=["OPR"])
        print(f"Found {len(results)} results")
        for i, result in enumerate(results, 1):
            content = result.get("content", {})
            space = content.get("space", {})
            print(f"{i}. {content.get('title', 'No title')}")
            print(f"   Space: {space.get('key', 'No key')} - {space.get('name', 'No name')}")
            print(f"   ID: {content.get('id', 'No ID')}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    # Test 4: Raw API call to see actual response structure
    print("=== Test 4: Raw API response inspection ===")
    try:
        cql = 'text ~ "skip by tag" AND (space = "OPR")'
        params = {
            "cql": cql,
            "limit": 2,
            "expand": "space,version"
        }
        print(f"CQL Query: {cql}")
        print(f"Expand: {params['expand']}")

        raw_result = client._make_request("GET", "content/search", params=params)
        print(f"Raw response keys: {list(raw_result.keys())}")
        print(f"Results count: {len(raw_result.get('results', []))}")

        if raw_result.get('results'):
            first_result = raw_result['results'][0]
            print("First result structure:")
            print(json.dumps(first_result, indent=2))

    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    # Test 4b: Try with search_confluence_content function directly
    print("=== Test 4b: Test fixed search_confluence_content function ===")
    try:
        from confluence_tools import search_confluence_content
        results = search_confluence_content("skip by tag", limit=3, spaces="OPR")
        print(f"Found {len(results)} results")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.get('title', 'No title')}")
            print(f"   Space: {result.get('space', {}).get('key', 'No key')} - {result.get('space', {}).get('name', 'No name')}")
            print(f"   ID: {result.get('id', 'No ID')}")
            print(f"   URL: {result.get('url', 'No URL')}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    # Test 5: List available spaces
    print("=== Test 5: List available spaces ===")
    try:
        spaces_result = client._make_request("GET", "space", params={"limit": 50})
        spaces = spaces_result.get("results", [])
        print(f"Found {len(spaces)} spaces:")
        for space in spaces[:10]:  # Show first 10
            print(f"  • {space.get('key')} - {space.get('name')}")
            if space.get('key') == 'OPR':
                print(f"    ✅ OPR space found!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_confluence_api()