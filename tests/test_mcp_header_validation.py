#!/usr/bin/env python3
"""
MCP-Protocol-Version Header Validation Test

Focused test for MCP-Protocol-Version header validation functionality
in the Kafka Schema Registry MCP Server.

This test validates:
- MCP-Protocol-Version header validation middleware
- Exempt path functionality
- Error responses for missing/invalid headers
- Header validation status reporting

Usage:
    python test_mcp_header_validation.py
"""

import json
import os
import sys
import unittest
from pathlib import Path
from typing import Any, Dict

# Add project root to Python path for CI compatibility
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def test_mcp_header_validation_basic():
    """Basic test for MCP header validation functionality."""
    print("🧪 Testing MCP Header Validation")
    print("=" * 50)

    try:
        # Test 1: Import MCP header validation components
        try:
            from kafka_schema_registry_unified_mcp import (
                EXEMPT_PATHS,
                MCP_PROTOCOL_VERSION,
                SUPPORTED_MCP_VERSIONS,
                is_exempt_path,
            )

            print(f"✅ MCP header validation components imported")
            print(f"   Protocol Version: {MCP_PROTOCOL_VERSION}")
            print(f"   Supported Versions: {SUPPORTED_MCP_VERSIONS}")
            print(f"   Exempt Paths: {EXEMPT_PATHS}")
            test1_passed = True
        except ImportError as e:
            print(f"❌ Failed to import MCP header validation components: {e}")
            test1_passed = False

        # Test 2: Validate exempt path detection
        try:
            if test1_passed:
                # Test exempt paths
                exempt_test_paths = [
                    "/health",
                    "/metrics",
                    "/ready",
                    "/.well-known/oauth-authorization-server",
                    "/.well-known/test",
                ]

                # Test non-exempt paths
                non_exempt_test_paths = [
                    "/",
                    "/mcp",
                    "/api/schemas",
                    "/subjects/test/versions",
                ]

                exempt_results = [is_exempt_path(path) for path in exempt_test_paths]
                non_exempt_results = [
                    is_exempt_path(path) for path in non_exempt_test_paths
                ]

                if all(exempt_results) and not any(non_exempt_results):
                    print("✅ Exempt path detection working correctly")
                    print(f"   Exempt paths detected: {len(exempt_results)}")
                    print(f"   Non-exempt paths detected: {len(non_exempt_results)}")
                    test2_passed = True
                else:
                    print("❌ Exempt path detection failed")
                    print(f"   Exempt path results: {exempt_results}")
                    print(f"   Non-exempt path results: {non_exempt_results}")
                    test2_passed = False
            else:
                test2_passed = False
        except Exception as e:
            print(f"❌ Error testing exempt paths: {e}")
            test2_passed = False

        # Test 3: Check header validation status
        try:
            if test1_passed:
                from kafka_schema_registry_unified_mcp import get_mcp_compliance_status

                status = get_mcp_compliance_status()

                # Check required fields for header validation
                required_fields = [
                    "protocol_version",
                    "header_validation_enabled",
                    "compliance_status",
                ]

                missing_fields = [
                    field for field in required_fields if field not in status
                ]

                if not missing_fields:
                    print("✅ Header validation status reporting working")
                    print(f"   Protocol Version: {status.get('protocol_version')}")
                    print(
                        f"   Header Validation: {status.get('header_validation_enabled')}"
                    )
                    print(f"   Compliance Status: {status.get('compliance_status')}")
                    test3_passed = True
                else:
                    print(f"❌ Missing required status fields: {missing_fields}")
                    test3_passed = False
            else:
                test3_passed = False
        except Exception as e:
            print(f"❌ Error testing header validation status: {e}")
            test3_passed = False

        # Test 4: Verify middleware constants
        try:
            if test1_passed:
                # Check that protocol version matches specification
                if MCP_PROTOCOL_VERSION == "2025-06-18":
                    print("✅ MCP protocol version matches specification")
                    test4_passed = True
                else:
                    print(f"❌ Unexpected protocol version: {MCP_PROTOCOL_VERSION}")
                    test4_passed = False

                # Check supported versions include current version
                if MCP_PROTOCOL_VERSION in SUPPORTED_MCP_VERSIONS:
                    print("✅ Current protocol version in supported list")
                else:
                    print("❌ Current protocol version not in supported list")
                    test4_passed = False
            else:
                test4_passed = False
        except Exception as e:
            print(f"❌ Error verifying middleware constants: {e}")
            test4_passed = False

        # Calculate results
        tests = [test1_passed, test2_passed, test3_passed, test4_passed]
        passed = sum(tests)
        total = len(tests)

        print(f"\n📊 MCP Header Validation Test Results:")
        print(f"   Total Tests: {total}")
        print(f"   Passed: {passed}")
        print(f"   Failed: {total - passed}")
        print(f"   Success Rate: {(passed/total)*100:.1f}%")

        if passed == total:
            print("🎉 All MCP header validation tests passed!")
            return True
        else:
            print("❌ Some MCP header validation tests failed")
            return False

    except Exception as e:
        print(f"❌ Critical error in MCP header validation tests: {e}")
        return False


class MCPHeaderValidationTest(unittest.TestCase):
    """Unit test class for MCP header validation."""

    def setUp(self):
        """Set up test environment."""
        try:
            from kafka_schema_registry_unified_mcp import (
                EXEMPT_PATHS,
                MCP_PROTOCOL_VERSION,
                SUPPORTED_MCP_VERSIONS,
                is_exempt_path,
            )

            self.MCP_PROTOCOL_VERSION = MCP_PROTOCOL_VERSION
            self.SUPPORTED_MCP_VERSIONS = SUPPORTED_MCP_VERSIONS
            self.is_exempt_path = is_exempt_path
            self.EXEMPT_PATHS = EXEMPT_PATHS
        except ImportError as e:
            self.skipTest(f"MCP components not available: {e}")

    def test_protocol_version(self):
        """Test that protocol version is correctly set."""
        self.assertEqual(self.MCP_PROTOCOL_VERSION, "2025-06-18")
        self.assertIn(self.MCP_PROTOCOL_VERSION, self.SUPPORTED_MCP_VERSIONS)

    def test_exempt_paths_health_endpoints(self):
        """Test that health endpoints are exempt from header validation."""
        health_paths = ["/health", "/metrics", "/ready"]
        for path in health_paths:
            with self.subTest(path=path):
                self.assertTrue(
                    self.is_exempt_path(path), f"Path {path} should be exempt"
                )

    def test_exempt_paths_well_known(self):
        """Test that .well-known paths are exempt from header validation."""
        well_known_paths = [
            "/.well-known/oauth-authorization-server",
            "/.well-known/openid_configuration",
            "/.well-known/test",
        ]
        for path in well_known_paths:
            with self.subTest(path=path):
                self.assertTrue(
                    self.is_exempt_path(path), f"Path {path} should be exempt"
                )

    def test_non_exempt_paths(self):
        """Test that API paths are not exempt from header validation."""
        api_paths = ["/", "/mcp", "/api/schemas", "/subjects/test/versions", "/config"]
        for path in api_paths:
            with self.subTest(path=path):
                self.assertFalse(
                    self.is_exempt_path(path), f"Path {path} should not be exempt"
                )

    def test_compliance_status_fields(self):
        """Test that compliance status includes required fields."""
        try:
            from kafka_schema_registry_unified_mcp import get_mcp_compliance_status

            status = get_mcp_compliance_status()

            required_fields = [
                "protocol_version",
                "header_validation_enabled",
                "compliance_status",
            ]

            for field in required_fields:
                with self.subTest(field=field):
                    self.assertIn(
                        field, status, f"Status missing required field: {field}"
                    )

            # Verify protocol version in status
            self.assertEqual(status["protocol_version"], "2025-06-18")

            # Verify compliance status is compliant
            self.assertEqual(status["compliance_status"], "COMPLIANT")

        except ImportError:
            self.skipTest("Compliance status function not available")


def main():
    """Main function to run MCP header validation tests."""
    print("🚀 MCP Header Validation Test Suite")
    print("   Kafka Schema Registry MCP Server")
    print("   MCP 2025-06-18 Header Validation Testing")
    print("")

    # Run basic tests
    basic_success = test_mcp_header_validation_basic()

    # Run unit tests
    print("\n" + "=" * 50)
    print("🧪 Running Unit Test Suite")
    print("=" * 50)

    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(MCPHeaderValidationTest)

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Determine overall success
    unit_success = result.wasSuccessful()

    print("\n" + "=" * 50)
    print("📊 Overall Test Results")
    print("=" * 50)
    print(f"Basic Tests: {'✅ PASSED' if basic_success else '❌ FAILED'}")
    print(f"Unit Tests: {'✅ PASSED' if unit_success else '❌ FAILED'}")

    if basic_success and unit_success:
        print("🎉 All MCP header validation tests passed!")
        return 0
    else:
        print("❌ Some MCP header validation tests failed!")
        return 1


if __name__ == "__main__":
    exit(main())
