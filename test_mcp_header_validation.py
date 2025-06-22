#!/usr/bin/env python3
"""
Test Suite for MCP-Protocol-Version Header Validation

This test suite validates the MCP 2025-06-18 specification compliance
for header validation in the Kafka Schema Registry MCP Server.

Tests cover:
- MCP-Protocol-Version header validation middleware
- Exempt path functionality
- Error responses for missing/invalid headers
- Header inclusion in all responses
- Integration with existing OAuth and monitoring endpoints

Usage:
    python test_mcp_header_validation.py
    python -m pytest test_mcp_header_validation.py -v
"""

import asyncio
import json
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

# Add the project root to the path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test constants
MCP_PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_MCP_VERSIONS = ["2025-06-18"]
EXEMPT_PATHS = ["/health", "/metrics", "/ready", "/.well-known"]

# Mock the required modules for testing
os.environ["SCHEMA_REGISTRY_URL"] = "http://localhost:8081"


class TestMCPProtocolVersionValidation(unittest.TestCase):
    """Test cases for MCP-Protocol-Version header validation."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a minimal FastAPI app for testing the middleware
        self.app = FastAPI()

        # Import and apply the middleware function
        from kafka_schema_registry_unified_mcp import (
            validate_mcp_protocol_version_middleware,
        )

        self.app.middleware("http")(validate_mcp_protocol_version_middleware)

        # Add test endpoints
        @self.app.get("/test")
        async def test_endpoint():
            return {"message": "test successful"}

        @self.app.get("/health")
        async def health_endpoint():
            return {"status": "healthy"}

        @self.app.get("/metrics")
        async def metrics_endpoint():
            return {"metrics": "data"}

        @self.app.get("/ready")
        async def ready_endpoint():
            return {"status": "ready"}

        @self.app.get("/.well-known/test")
        async def well_known_endpoint():
            return {"well_known": "data"}

        self.client = TestClient(self.app)

    def test_missing_header_returns_400(self):
        """Test that missing MCP-Protocol-Version header returns 400."""
        response = self.client.get("/test")

        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing MCP-Protocol-Version header", response.json()["error"])
        self.assertEqual(
            response.headers.get("MCP-Protocol-Version"), MCP_PROTOCOL_VERSION
        )

    def test_invalid_header_returns_400(self):
        """Test that invalid MCP-Protocol-Version header returns 400."""
        headers = {"MCP-Protocol-Version": "invalid-version"}
        response = self.client.get("/test", headers=headers)

        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported MCP-Protocol-Version", response.json()["error"])
        self.assertEqual(
            response.headers.get("MCP-Protocol-Version"), MCP_PROTOCOL_VERSION
        )

    def test_valid_header_passes_validation(self):
        """Test that valid MCP-Protocol-Version header passes validation."""
        headers = {"MCP-Protocol-Version": MCP_PROTOCOL_VERSION}
        response = self.client.get("/test", headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "test successful")
        self.assertEqual(
            response.headers.get("MCP-Protocol-Version"), MCP_PROTOCOL_VERSION
        )

    def test_health_endpoint_exempt_from_validation(self):
        """Test that /health endpoint is exempt from header validation."""
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")
        self.assertEqual(
            response.headers.get("MCP-Protocol-Version"), MCP_PROTOCOL_VERSION
        )

    def test_metrics_endpoint_exempt_from_validation(self):
        """Test that /metrics endpoint is exempt from header validation."""
        response = self.client.get("/metrics")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["metrics"], "data")
        self.assertEqual(
            response.headers.get("MCP-Protocol-Version"), MCP_PROTOCOL_VERSION
        )

    def test_ready_endpoint_exempt_from_validation(self):
        """Test that /ready endpoint is exempt from header validation."""
        response = self.client.get("/ready")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ready")
        self.assertEqual(
            response.headers.get("MCP-Protocol-Version"), MCP_PROTOCOL_VERSION
        )

    def test_well_known_endpoint_exempt_from_validation(self):
        """Test that /.well-known/* endpoints are exempt from header validation."""
        response = self.client.get("/.well-known/test")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["well_known"], "data")
        self.assertEqual(
            response.headers.get("MCP-Protocol-Version"), MCP_PROTOCOL_VERSION
        )

    def test_error_response_format(self):
        """Test the format of error responses for missing headers."""
        response = self.client.get("/test")

        self.assertEqual(response.status_code, 400)
        error_data = response.json()

        # Verify required fields in error response
        self.assertIn("error", error_data)
        self.assertIn("details", error_data)
        self.assertIn("supported_versions", error_data)
        self.assertIn("example", error_data)

        # Verify supported versions
        self.assertEqual(error_data["supported_versions"], SUPPORTED_MCP_VERSIONS)

        # Verify example header format
        self.assertIn("MCP-Protocol-Version: 2025-06-18", error_data["example"])

    def test_all_responses_include_header(self):
        """Test that all responses include the MCP-Protocol-Version header."""
        test_cases = [
            ("/health", {}),  # Exempt endpoint without header
            ("/test", {"MCP-Protocol-Version": MCP_PROTOCOL_VERSION}),  # Valid request
            ("/test", {}),  # Invalid request (should still include header in error)
        ]

        for path, headers in test_cases:
            response = self.client.get(path, headers=headers)
            self.assertEqual(
                response.headers.get("MCP-Protocol-Version"),
                MCP_PROTOCOL_VERSION,
                f"Missing header in response for {path}",
            )


class TestMCPComplianceIntegration(unittest.TestCase):
    """Integration tests for MCP compliance with existing functionality."""

    def setUp(self):
        """Set up integration test fixtures."""
        # Mock environment variables
        self.env_patcher = patch.dict(
            os.environ,
            {
                "SCHEMA_REGISTRY_URL": "http://localhost:8081",
                "ENABLE_AUTH": "false",
                "REGISTRIES_CONFIG": "",
            },
        )
        self.env_patcher.start()

    def tearDown(self):
        """Clean up patches."""
        self.env_patcher.stop()

    @patch("kafka_schema_registry_unified_mcp.registry_manager")
    def test_compliance_status_tool(self, mock_registry_manager):
        """Test the MCP compliance status tool includes header validation info."""
        # Mock registry manager
        mock_registry_manager.list_registries.return_value = ["test-registry"]

        # Import and test the compliance function
        from kafka_schema_registry_unified_mcp import get_mcp_compliance_status

        result = get_mcp_compliance_status()

        # Verify compliance information
        self.assertEqual(result["protocol_version"], MCP_PROTOCOL_VERSION)
        self.assertEqual(result["supported_versions"], SUPPORTED_MCP_VERSIONS)
        self.assertTrue(result["header_validation_enabled"])
        self.assertTrue(result["jsonrpc_batching_disabled"])
        self.assertEqual(result["compliance_status"], "COMPLIANT")

        # Verify header validation configuration
        header_validation = result["header_validation"]
        self.assertEqual(header_validation["required_header"], "MCP-Protocol-Version")
        self.assertEqual(
            header_validation["supported_versions"], SUPPORTED_MCP_VERSIONS
        )
        self.assertEqual(header_validation["exempt_paths"], EXEMPT_PATHS)
        self.assertTrue(header_validation["validation_active"])
        self.assertEqual(header_validation["error_response_code"], 400)

    def test_exempt_path_detection(self):
        """Test the exempt path detection function."""
        from kafka_schema_registry_unified_mcp import is_exempt_path

        # Test exempt paths
        exempt_test_cases = [
            "/health",
            "/metrics",
            "/ready",
            "/.well-known/oauth-authorization-server",
            "/.well-known/jwks.json",
            "/.well-known/test",
        ]

        for path in exempt_test_cases:
            self.assertTrue(is_exempt_path(path), f"Path {path} should be exempt")

        # Test non-exempt paths
        non_exempt_test_cases = [
            "/mcp",
            "/api/test",
            "/some/other/path",
            "/healthcheck",  # Similar but not exact match
            "/well-known",  # Missing leading dot
        ]

        for path in non_exempt_test_cases:
            self.assertFalse(is_exempt_path(path), f"Path {path} should not be exempt")


class TestLiveServerValidation(unittest.TestCase):
    """Live server tests for header validation (requires running server)."""

    def setUp(self):
        """Set up live server test fixtures."""
        self.server_url = os.getenv("TEST_SERVER_URL", "http://localhost:8000")
        self.timeout = 10

    def test_live_server_health_endpoint(self):
        """Test live server health endpoint includes MCP header."""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=self.timeout)

            # Health endpoint should always work (exempt from validation)
            self.assertEqual(response.status_code, 200)

            # Should include MCP-Protocol-Version header
            self.assertEqual(
                response.headers.get("MCP-Protocol-Version"), MCP_PROTOCOL_VERSION
            )

            # Should include compliance information
            data = response.json()
            if "mcp_protocol_version" in data:
                self.assertEqual(data["mcp_protocol_version"], MCP_PROTOCOL_VERSION)

        except requests.exceptions.ConnectionError:
            self.skipTest("Live server not available for testing")

    def test_live_server_metrics_endpoint(self):
        """Test live server metrics endpoint includes MCP header."""
        try:
            response = requests.get(f"{self.server_url}/metrics", timeout=self.timeout)

            # Metrics endpoint should always work (exempt from validation)
            self.assertEqual(response.status_code, 200)

            # Should include MCP-Protocol-Version header
            self.assertEqual(
                response.headers.get("MCP-Protocol-Version"), MCP_PROTOCOL_VERSION
            )

        except requests.exceptions.ConnectionError:
            self.skipTest("Live server not available for testing")

    def test_live_server_oauth_discovery_endpoints(self):
        """Test OAuth discovery endpoints include MCP headers."""
        try:
            oauth_endpoints = [
                "/.well-known/oauth-authorization-server-custom",
                "/.well-known/oauth-protected-resource",
                "/.well-known/jwks.json",
            ]

            for endpoint in oauth_endpoints:
                response = requests.get(
                    f"{self.server_url}{endpoint}", timeout=self.timeout
                )

                # These endpoints should be exempt and include the header
                # (They may return 404 if OAuth is disabled, but should still include header)
                self.assertIn(response.status_code, [200, 404])
                self.assertEqual(
                    response.headers.get("MCP-Protocol-Version"),
                    MCP_PROTOCOL_VERSION,
                    f"Missing header in {endpoint}",
                )

        except requests.exceptions.ConnectionError:
            self.skipTest("Live server not available for testing")


def create_test_client_with_headers():
    """Create a test client with proper MCP headers for testing MCP endpoints."""

    def make_request(method, url, **kwargs):
        headers = kwargs.get("headers", {})
        headers["MCP-Protocol-Version"] = MCP_PROTOCOL_VERSION
        kwargs["headers"] = headers
        return getattr(requests, method.lower())(url, **kwargs)

    return make_request


class TestMCPEndpointValidation(unittest.TestCase):
    """Test MCP endpoint validation with proper headers."""

    def setUp(self):
        """Set up MCP endpoint test fixtures."""
        self.server_url = os.getenv("TEST_SERVER_URL", "http://localhost:8000")
        self.mcp_url = f"{self.server_url}/mcp"
        self.timeout = 10
        self.request_with_headers = create_test_client_with_headers()

    def test_mcp_endpoint_requires_header(self):
        """Test that MCP endpoint requires the protocol version header."""
        try:
            # Request without header should fail
            response = requests.post(self.mcp_url, json={}, timeout=self.timeout)
            self.assertEqual(response.status_code, 400)

            # Request with header should proceed (might fail for other reasons, but not header validation)
            headers = {"MCP-Protocol-Version": MCP_PROTOCOL_VERSION}
            response = requests.post(
                self.mcp_url, json={}, headers=headers, timeout=self.timeout
            )

            # Should not fail due to missing header (might fail for other reasons like invalid JSON-RPC)
            self.assertNotEqual(response.status_code, 400)

        except requests.exceptions.ConnectionError:
            self.skipTest("Live server not available for testing")


def run_comprehensive_header_validation_test():
    """Run a comprehensive test of header validation functionality."""
    print("🧪 Running Comprehensive MCP-Protocol-Version Header Validation Tests")
    print("=" * 80)

    test_results = {
        "middleware_tests": False,
        "integration_tests": False,
        "live_server_tests": False,
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
    }

    # Run middleware tests
    print("\n📋 Running Middleware Tests...")
    try:
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(TestMCPProtocolVersionValidation)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        test_results["middleware_tests"] = result.wasSuccessful()
        test_results["total_tests"] += result.testsRun
        test_results["passed_tests"] += (
            result.testsRun - len(result.failures) - len(result.errors)
        )
        test_results["failed_tests"] += len(result.failures) + len(result.errors)

        print(
            f"✅ Middleware Tests: {'PASSED' if result.wasSuccessful() else 'FAILED'}"
        )

    except Exception as e:
        print(f"❌ Middleware Tests: FAILED - {e}")

    # Run integration tests
    print("\n🔗 Running Integration Tests...")
    try:
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(TestMCPComplianceIntegration)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        test_results["integration_tests"] = result.wasSuccessful()
        test_results["total_tests"] += result.testsRun
        test_results["passed_tests"] += (
            result.testsRun - len(result.failures) - len(result.errors)
        )
        test_results["failed_tests"] += len(result.failures) + len(result.errors)

        print(
            f"✅ Integration Tests: {'PASSED' if result.wasSuccessful() else 'FAILED'}"
        )

    except Exception as e:
        print(f"❌ Integration Tests: FAILED - {e}")

    # Run live server tests
    print("\n🌐 Running Live Server Tests...")
    try:
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(TestLiveServerValidation)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        test_results["live_server_tests"] = result.wasSuccessful()
        test_results["total_tests"] += result.testsRun
        test_results["passed_tests"] += (
            result.testsRun - len(result.failures) - len(result.errors)
        )
        test_results["failed_tests"] += len(result.failures) + len(result.errors)

        print(
            f"✅ Live Server Tests: {'PASSED' if result.wasSuccessful() else 'FAILED'}"
        )

    except Exception as e:
        print(f"❌ Live Server Tests: FAILED - {e}")

    # Print summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests:  {test_results['total_tests']}")
    print(f"Passed Tests: {test_results['passed_tests']}")
    print(f"Failed Tests: {test_results['failed_tests']}")
    print(
        f"Success Rate: {(test_results['passed_tests'] / test_results['total_tests'] * 100):.1f}%"
    )

    all_passed = (
        test_results["middleware_tests"]
        and test_results["integration_tests"]
        and test_results["live_server_tests"]
    )

    print(
        f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}"
    )

    if all_passed:
        print("\n🎉 MCP-Protocol-Version header validation is working correctly!")
        print("✅ MCP 2025-06-18 specification compliance: ACHIEVED")
    else:
        print("\n⚠️  Some tests failed. Please review the implementation.")

    return test_results


def demonstrate_header_validation():
    """Demonstrate the header validation functionality with examples."""
    print("\n📚 MCP-Protocol-Version Header Validation Demonstration")
    print("=" * 60)

    examples = [
        {
            "name": "Valid Request with Header",
            "headers": {"MCP-Protocol-Version": "2025-06-18"},
            "expected_status": "✅ Should succeed (200 or normal processing)",
        },
        {
            "name": "Missing Header",
            "headers": {},
            "expected_status": "❌ Should fail with 400 Bad Request",
        },
        {
            "name": "Invalid Header Version",
            "headers": {"MCP-Protocol-Version": "invalid-version"},
            "expected_status": "❌ Should fail with 400 Bad Request",
        },
        {
            "name": "Health Endpoint (Exempt)",
            "path": "/health",
            "headers": {},
            "expected_status": "✅ Should succeed (exempt from validation)",
        },
        {
            "name": "Well-known Endpoint (Exempt)",
            "path": "/.well-known/test",
            "headers": {},
            "expected_status": "✅ Should succeed (exempt from validation)",
        },
    ]

    for example in examples:
        print(f"\n📝 {example['name']}:")
        print(f"   Headers: {example['headers']}")
        print(f"   Path: {example.get('path', '/mcp')}")
        print(f"   Expected: {example['expected_status']}")

    print("\n🔧 Implementation Details:")
    print(f"   • Supported MCP Protocol Version: {MCP_PROTOCOL_VERSION}")
    print(f"   • Exempt Paths: {EXEMPT_PATHS}")
    print("   • Error Response: 400 Bad Request with detailed error message")
    print("   • All responses include MCP-Protocol-Version header")
    print("   • Middleware validates before request processing")


if __name__ == "__main__":
    print("🚀 MCP-Protocol-Version Header Validation Test Suite")
    print("   For Kafka Schema Registry MCP Server")
    print("   MCP 2025-06-18 Specification Compliance")

    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demonstrate_header_validation()
    else:
        run_comprehensive_header_validation_test()

    print("\n💡 Usage Tips:")
    print("   • Run with --demo flag to see demonstration of functionality")
    print("   • Set TEST_SERVER_URL environment variable to test against live server")
    print(
        "   • Use 'python -m pytest test_mcp_header_validation.py -v' for detailed pytest output"
    )
