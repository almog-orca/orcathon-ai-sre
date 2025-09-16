#!/usr/bin/env python3
"""
Confluence Connection Test Utility
Tests various authentication methods and API endpoints to diagnose connectivity issues.
"""

import os
import dotenv
import requests
import base64
from typing import Dict, Any, Optional

# Load environment variables
dotenv.load_dotenv()

class ConfluenceConnectionTester:
    def __init__(self):
        self.base_url = os.getenv('CONFLUENCE_BASE_URL', '').rstrip('/')
        self.token = os.getenv('CONFLUENCE_TOKEN', '')
        self.email = os.getenv('CONFLUENCE_EMAIL', '')
        self.api_base = f"{self.base_url}/wiki/rest/api"

    def test_bearer_auth(self) -> Dict[str, Any]:
        """Test Bearer token authentication."""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            # Test basic user info endpoint
            response = requests.get(f"{self.api_base}/user/current", headers=headers, timeout=10)
            return {
                "method": "Bearer Token",
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response": response.json() if response.status_code == 200 else response.text[:200]
            }
        except Exception as e:
            return {
                "method": "Bearer Token",
                "success": False,
                "error": str(e)
            }

    def test_basic_auth(self, email: str) -> Dict[str, Any]:
        """Test Basic authentication with email."""
        auth_string = base64.b64encode(f"{email}:{self.token}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth_string}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            response = requests.get(f"{self.api_base}/user/current", headers=headers, timeout=10)
            return {
                "method": f"Basic Auth ({email})",
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response": response.json() if response.status_code == 200 else response.text[:200]
            }
        except Exception as e:
            return {
                "method": f"Basic Auth ({email})",
                "success": False,
                "error": str(e)
            }

    def test_space_access(self, auth_headers: Dict[str, str], space_key: str = "OPR") -> Dict[str, Any]:
        """Test access to specific space."""
        try:
            # Test space info endpoint
            response = requests.get(f"{self.api_base}/space/{space_key}", headers=auth_headers, timeout=10)
            return {
                "test": f"Space Access ({space_key})",
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response": response.json() if response.status_code == 200 else response.text[:200]
            }
        except Exception as e:
            return {
                "test": f"Space Access ({space_key})",
                "success": False,
                "error": str(e)
            }

    def test_search_permissions(self, auth_headers: Dict[str, str]) -> Dict[str, Any]:
        """Test search API permissions."""
        try:
            # Simple search test
            params = {
                "cql": "type=page",
                "limit": 1
            }
            response = requests.get(f"{self.api_base}/content/search", headers=auth_headers, params=params, timeout=10)
            return {
                "test": "Search API",
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response": response.json() if response.status_code == 200 else response.text[:200]
            }
        except Exception as e:
            return {
                "test": "Search API",
                "success": False,
                "error": str(e)
            }

    def test_list_spaces(self, auth_headers: Dict[str, str]) -> Dict[str, Any]:
        """Test listing available spaces."""
        try:
            params = {"limit": 10}
            response = requests.get(f"{self.api_base}/space", headers=auth_headers, params=params, timeout=10)

            result = {
                "test": "List Spaces",
                "status_code": response.status_code,
                "success": response.status_code == 200
            }

            if response.status_code == 200:
                data = response.json()
                spaces = data.get('results', [])
                result["spaces_found"] = len(spaces)
                result["space_keys"] = [s.get('key') for s in spaces[:5]]  # First 5 space keys
            else:
                result["response"] = response.text[:200]

            return result
        except Exception as e:
            return {
                "test": "List Spaces",
                "success": False,
                "error": str(e)
            }

    def test_different_urls(self) -> Dict[str, Any]:
        """Test different URL formats to find the correct one."""
        base_domain = "https://orcasecurity.atlassian.net"
        url_variants = [
            f"{base_domain}/wiki/rest/api",
            f"{base_domain}/rest/api",
            f"{base_domain}/api"
        ]

        # Use basic auth with provided email
        auth_string = base64.b64encode(f"{self.email}:{self.token}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth_string}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        results = {}
        for url in url_variants:
            try:
                response = requests.get(f"{url}/user/current", headers=headers, timeout=10)
                results[url] = {
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "response": response.json() if response.status_code == 200 else response.text[:100]
                }
            except Exception as e:
                results[url] = {
                    "success": False,
                    "error": str(e)
                }

        return results

    def run_full_test(self) -> None:
        """Run comprehensive connection tests."""
        print("🔍 Confluence Connection Test")
        print("=" * 50)
        print(f"Base URL: {self.base_url}")
        print(f"Email: {self.email}")
        print(f"Token: {self.token[:20]}..." if self.token else "No token found")
        print()

        if not self.base_url or not self.token:
            print("❌ Missing CONFLUENCE_BASE_URL or CONFLUENCE_TOKEN in .env file")
            return

        if not self.email:
            print("❌ Missing CONFLUENCE_EMAIL in .env file")
            return

        # Test 1: URL Format Testing
        print("1️⃣ Testing Different URL Formats...")
        url_results = self.test_different_urls()
        for url, result in url_results.items():
            print(f"   {url}")
            if result.get('success'):
                print(f"      ✅ SUCCESS - Status: {result['status_code']}")
            else:
                print(f"      ❌ FAILED - Status: {result.get('status_code', 'N/A')}")
                if 'error' in result:
                    print(f"         Error: {result['error']}")

        # Test 2: Basic Auth with provided email
        print(f"\n2️⃣ Testing Basic Authentication with {self.email}...")
        basic_result = self.test_basic_auth(self.email)
        self._print_result(basic_result)

        basic_success = basic_result.get('success')
        if basic_success:
            auth_string = base64.b64encode(f"{self.email}:{self.token}".encode()).decode()
            successful_headers = {
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        else:
            successful_headers = None

        # Test 3: Bearer Token Authentication
        print("\n3️⃣ Testing Bearer Token Authentication...")
        bearer_result = self.test_bearer_auth()
        self._print_result(bearer_result)

        # If no auth method worked, stop here
        if not bearer_result.get('success') and not basic_success:
            print("\n❌ All authentication methods failed. Check your token permissions.")
            return

        # Use successful headers for further tests
        if bearer_result.get('success'):
            test_headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        else:
            test_headers = successful_headers

        # Test 4: List Available Spaces
        print("\n4️⃣ Testing Space Listing...")
        spaces_result = self.test_list_spaces(test_headers)
        self._print_result(spaces_result)

        # Test 5: OPR Space Access
        print("\n5️⃣ Testing OPR Space Access...")
        opr_result = self.test_space_access(test_headers, "OPR")
        self._print_result(opr_result)

        # Test 6: Search API Permissions
        print("\n6️⃣ Testing Search API Permissions...")
        search_result = self.test_search_permissions(test_headers)
        self._print_result(search_result)

        print("\n" + "=" * 50)
        print("🏁 Test Summary:")

        if bearer_result.get('success') or basic_success:
            print("✅ Authentication: WORKING")
        else:
            print("❌ Authentication: FAILED")

        if spaces_result.get('success'):
            print(f"✅ Space Access: WORKING ({spaces_result.get('spaces_found', 'unknown')} spaces found)")
        else:
            print("❌ Space Access: FAILED")

        if search_result.get('success'):
            print("✅ Search API: WORKING")
        else:
            print("❌ Search API: FAILED")

    def _print_result(self, result: Dict[str, Any]) -> None:
        """Print formatted test result."""
        method = result.get('method', result.get('test', 'Test'))

        if result.get('success'):
            print(f"   ✅ {method}: SUCCESS")
            if 'spaces_found' in result:
                print(f"      Found {result['spaces_found']} spaces: {result.get('space_keys', [])}")
        else:
            print(f"   ❌ {method}: FAILED")
            if 'status_code' in result:
                print(f"      Status: {result['status_code']}")
            if 'error' in result:
                print(f"      Error: {result['error']}")
            elif 'response' in result:
                print(f"      Response: {result['response']}")


if __name__ == "__main__":
    tester = ConfluenceConnectionTester()
    tester.run_full_test()