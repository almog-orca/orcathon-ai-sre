#!/usr/bin/env python3
"""
Coralogix Connection Test Utility
Tests various API endpoints and query capabilities to diagnose connectivity and functionality.
"""

import os
import dotenv
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List

# Load environment variables
dotenv.load_dotenv()

# Import Coralogix tools
from coralogix_tools import (
    init_coralogix_client,
    get_coralogix_client,
    query_coralogix_logs,
    query_coralogix_logs_last_24h,
    query_coralogix_logs_last_hour,
    query_coralogix_logs_custom_hours,
    query_coralogix_error_logs_24h,
    query_coralogix_logs_by_service,
    get_lucene_query_examples
)


class CoralogixConnectionTester:
    def __init__(self):
        self.api_key = os.getenv('CORALOGIX_PRIVATE_KEY') or os.getenv('CORALOGIX_API_KEY')
        self.base_url = "https://api.coralogix.com"
        self.client_initialized = False

    def test_client_initialization(self) -> Dict[str, Any]:
        """Test Coralogix client initialization."""
        try:
            if not self.api_key:
                return {
                    "test": "Client Initialization",
                    "success": False,
                    "error": "CORALOGIX_PRIVATE_KEY environment variable not found"
                }

            init_coralogix_client(self.api_key)
            self.client_initialized = True
            
            return {
                "test": "Client Initialization",
                "success": True,
                "message": "Coralogix client initialized successfully"
            }
        except Exception as e:
            return {
                "test": "Client Initialization",
                "success": False,
                "error": str(e)
            }

    def test_basic_query(self) -> Dict[str, Any]:
        """Test basic log query with wildcard."""
        try:
            # Use the client method directly
            client = get_coralogix_client()
            result = client.query_logs_last_minutes("*", minutes=60, limit=5)
            
            if "error" in result:
                return {
                    "test": "Basic Query (last hour)",
                    "success": False,
                    "error": result["error"]
                }
            
            logs = result.get("logs", [])
            return {
                "test": "Basic Query (last hour)",
                "success": True,
                "logs_found": len(logs),
                "sample_log": logs[0] if logs else None
            }
                
        except Exception as e:
            return {
                "test": "Basic Query (last hour)",
                "success": False,
                "error": str(e)
            }

    def test_error_logs_query(self) -> Dict[str, Any]:
        """Test error logs query."""
        try:
            client = get_coralogix_client()
            result = client.query_logs_last_hours("level:ERROR", hours=24, limit=3)
            
            if "error" in result:
                return {
                    "test": "Error Logs Query (24h)",
                    "success": False,
                    "error": result["error"]
                }
            
            logs = result.get("logs", [])
            return {
                "test": "Error Logs Query (24h)",
                "success": True,
                "error_logs_found": len(logs),
                "sample_error": logs[0] if logs else None
            }
                
        except Exception as e:
            return {
                "test": "Error Logs Query (24h)",
                "success": False,
                "error": str(e)
            }

    def test_lucene_query_syntax(self) -> Dict[str, Any]:
        """Test Lucene query syntax with specific filters."""
        try:
            # Test a more specific Lucene query
            client = get_coralogix_client()
            result = client.query_logs_last_hours("level:ERROR OR level:WARN", hours=24, limit=5)
            
            if "error" in result:
                return {
                    "test": "Lucene Query Syntax",
                    "success": False,
                    "error": result["error"]
                }
            
            logs = result.get("logs", [])
            return {
                "test": "Lucene Query Syntax",
                "success": True,
                "query_used": "level:ERROR OR level:WARN",
                "logs_found": len(logs),
                "log_levels": list(set([log.get('level') for log in logs if log.get('level')])) if logs else []
            }
                
        except Exception as e:
            return {
                "test": "Lucene Query Syntax",
                "success": False,
                "error": str(e)
            }

    def test_service_specific_query(self) -> Dict[str, Any]:
        """Test service-specific log query."""
        try:
            # Try common service names
            service_names = ["api", "auth", "web", "backend", "frontend"]
            client = get_coralogix_client()
            
            for service in service_names:
                # Build query to match service in multiple possible fields
                service_query = f"(service:{service} OR source:{service} OR application:{service})"
                result = client.query_logs_last_hours(service_query, hours=24, limit=3)
                
                if "error" not in result:
                    logs = result.get("logs", [])
                    if len(logs) > 0:
                        return {
                            "test": "Service-Specific Query",
                            "success": True,
                            "service_tested": service,
                            "logs_found": len(logs),
                            "sample_log": logs[0]
                        }
            
            # If no service had logs, it's still successful
            return {
                "test": "Service-Specific Query",
                "success": True,
                "message": f"No logs found for tested services: {service_names}",
                "services_tested": service_names
            }
                
        except Exception as e:
            return {
                "test": "Service-Specific Query",
                "success": False,
                "error": str(e)
            }

    def test_custom_timeframe(self) -> Dict[str, Any]:
        """Test custom timeframe query."""
        try:
            # Query logs from 2 hours ago to 1 hour ago
            end_time = datetime.now(timezone.utc) - timedelta(hours=1)
            start_time = end_time - timedelta(hours=1)
            
            start_time_iso = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_time_iso = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            client = get_coralogix_client()
            result = client.query_logs("*", start_time_iso, end_time_iso, limit=3)
            
            if "error" in result:
                return {
                    "test": "Custom Timeframe Query",
                    "success": False,
                    "error": result["error"]
                }
            
            logs = result.get("logs", [])
            return {
                "test": "Custom Timeframe Query",
                "success": True,
                "timeframe": f"{start_time_iso} to {end_time_iso}",
                "logs_found": len(logs)
            }
                
        except Exception as e:
            return {
                "test": "Custom Timeframe Query",
                "success": False,
                "error": str(e)
            }

    def test_query_examples(self) -> Dict[str, Any]:
        """Test the query examples functionality."""
        try:
            examples = get_lucene_query_examples()
            
            if isinstance(examples, dict) and len(examples) > 0:
                return {
                    "test": "Query Examples",
                    "success": True,
                    "examples_count": len(examples),
                    "sample_examples": dict(list(examples.items())[:3])  # First 3 examples
                }
            else:
                return {
                    "test": "Query Examples",
                    "success": False,
                    "error": "No examples returned or invalid format"
                }
                
        except Exception as e:
            return {
                "test": "Query Examples",
                "success": False,
                "error": str(e)
            }

    def run_full_test(self) -> None:
        """Run comprehensive Coralogix connection and functionality tests."""
        print("🔍 Coralogix Tools Connection Test")
        print("=" * 50)
        print(f"Base URL: {self.base_url}")
        print(f"API Key: {self.api_key[:20]}..." if self.api_key else "No API key found")
        print()

        # Test 1: Client Initialization
        print("1️⃣ Testing Client Initialization...")
        init_result = self.test_client_initialization()
        self._print_result(init_result)

        if not init_result.get('success'):
            print("\n❌ Client initialization failed. Cannot proceed with API tests.")
            print("   Please check your CORALOGIX_PRIVATE_KEY in the .env file.")
            return

        # Test 2: Query Examples
        print("\n2️⃣ Testing Query Examples...")
        examples_result = self.test_query_examples()
        self._print_result(examples_result)

        if examples_result.get('success'):
            print("   📋 Available query patterns:")
            examples = examples_result.get('sample_examples', {})
            for name, query in examples.items():
                print(f"      {name}: {query}")

        # Test 3: Basic Query
        print("\n3️⃣ Testing Basic Log Query...")
        basic_result = self.test_basic_query()
        self._print_result(basic_result)

        # Test 4: Error Logs Query
        print("\n4️⃣ Testing Error Logs Query...")
        error_result = self.test_error_logs_query()
        self._print_result(error_result)

        # Test 5: Lucene Query Syntax
        print("\n5️⃣ Testing Lucene Query Syntax...")
        lucene_result = self.test_lucene_query_syntax()
        self._print_result(lucene_result)

        # Test 6: Service-Specific Query
        print("\n6️⃣ Testing Service-Specific Query...")
        service_result = self.test_service_specific_query()
        self._print_result(service_result)

        # Test 7: Custom Timeframe
        print("\n7️⃣ Testing Custom Timeframe Query...")
        timeframe_result = self.test_custom_timeframe()
        self._print_result(timeframe_result)

        # Test Summary
        print("\n" + "=" * 50)
        print("🏁 Test Summary:")

        tests = [
            ("Client Initialization", init_result),
            ("Query Examples", examples_result),
            ("Basic Query", basic_result),
            ("Error Logs Query", error_result),
            ("Lucene Syntax", lucene_result),
            ("Service Query", service_result),
            ("Custom Timeframe", timeframe_result)
        ]

        passed_tests = 0
        total_tests = len(tests)

        for test_name, result in tests:
            if result.get('success'):
                print(f"✅ {test_name}: WORKING")
                passed_tests += 1
            else:
                print(f"❌ {test_name}: FAILED")

        print(f"\n📊 Results: {passed_tests}/{total_tests} tests passed")

        if passed_tests == total_tests:
            print("🎉 All tests passed! Coralogix tools are working correctly.")
        elif passed_tests >= total_tests * 0.7:  # 70% pass rate
            print("⚠️  Most tests passed. Some features may need attention.")
        else:
            print("❌ Many tests failed. Check your API configuration and permissions.")

        print("\n💡 Usage Tips:")
        print("  - Use query_coralogix_logs_last_24h() for recent logs")
        print("  - Use query_coralogix_error_logs_24h() for error analysis")
        print("  - Use Lucene syntax like 'level:ERROR AND service:myapp'")
        print("  - Common fields: level, message, service, source, application")

    def _print_result(self, result: Dict[str, Any]) -> None:
        """Print formatted test result."""
        test_name = result.get('test', 'Test')

        if result.get('success'):
            print(f"   ✅ {test_name}: SUCCESS")
            
            # Print additional success information
            if 'logs_found' in result:
                print(f"      Logs found: {result['logs_found']}")
            if 'error_logs_found' in result:
                print(f"      Error logs found: {result['error_logs_found']}")
            if 'examples_count' in result:
                print(f"      Examples available: {result['examples_count']}")
            if 'query_used' in result:
                print(f"      Query: {result['query_used']}")
            if 'service_tested' in result:
                print(f"      Service tested: {result['service_tested']}")
            if 'timeframe' in result:
                print(f"      Timeframe: {result['timeframe']}")
            if 'message' in result:
                print(f"      Info: {result['message']}")
                
        else:
            print(f"   ❌ {test_name}: FAILED")
            if 'error' in result:
                print(f"      Error: {result['error']}")


if __name__ == "__main__":
    tester = CoralogixConnectionTester()
    tester.run_full_test()