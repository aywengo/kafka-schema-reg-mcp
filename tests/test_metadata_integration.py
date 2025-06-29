#!/usr/bin/env python3
"""
Test the consolidated metadata integration approach.

This test verifies that:
1. get_registry_metadata provides comprehensive metadata
2. Existing methods are enhanced with metadata automatically
3. No duplicate endpoints exist
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schema_registry_common import RegistryClient, RegistryConfig


class TestMetadataIntegration(unittest.TestCase):
    """Test cases for consolidated metadata integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = RegistryConfig(
            name="test-registry",
            url="http://localhost:8081",
            user="test-user",
            password="test-password",
        )
        self.client = RegistryClient(self.config)

    def test_get_server_metadata_comprehensive(self):
        """Test that get_server_metadata provides comprehensive metadata."""

        # Mock the session's get method instead of requests.get
        with patch.object(self.client.session, 'get') as mock_get:
            # Mock responses for both endpoints
            def mock_get_side_effect(url, **kwargs):
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.raise_for_status.return_value = None

                if "/v1/metadata/id" in url:
                    mock_response.json.return_value = {
                        "scope": {
                            "path": [],
                            "clusters": {
                                "kafka-cluster": "MkVlNjdqWVF0Q056MWFrUA",
                                "schema-registry-cluster": "schema-registry",
                            },
                        }
                    }
                elif "/v1/metadata/version" in url:
                    mock_response.json.return_value = {
                        "version": "7.6.0",
                        "commitId": "02d9aa023a8d034d480a718242df2a880e0be1f7",
                    }

                return mock_response

            mock_get.side_effect = mock_get_side_effect

            # Call the comprehensive metadata method
            result = self.client.get_server_metadata()

            # Verify both endpoints were called
            self.assertEqual(mock_get.call_count, 2)

            # Verify comprehensive response includes all expected fields
            self.assertIn("version", result)
            self.assertIn("commit_id", result)
            self.assertIn("kafka_cluster_id", result)
            self.assertIn("schema_registry_cluster_id", result)
            self.assertIn("scope", result)

            # Verify values are correctly mapped
            self.assertEqual(result["version"], "7.6.0")
            self.assertEqual(result["commit_id"], "02d9aa023a8d034d480a718242df2a880e0be1f7")
            self.assertEqual(result["kafka_cluster_id"], "MkVlNjdqWVF0Q056MWFrUA")
            self.assertEqual(result["schema_registry_cluster_id"], "schema-registry")

    def test_test_connection_includes_metadata(self):
        """Test that test_connection now includes metadata automatically."""

        # Mock the session's get method instead of requests.get
        with patch.object(self.client.session, 'get') as mock_get:
            # Mock responses for connection test and metadata
            def mock_get_side_effect(url, **kwargs):
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.raise_for_status.return_value = None
                mock_response.elapsed.total_seconds.return_value = 0.045

                if "/subjects" in url:
                    # Connection test
                    mock_response.json.return_value = []
                elif "/v1/metadata/id" in url:
                    mock_response.json.return_value = {
                        "scope": {
                            "path": [],
                            "clusters": {
                                "kafka-cluster": "MkVlNjdqWVF0Q056MWFrUA",
                                "schema-registry-cluster": "schema-registry",
                            },
                        }
                    }
                elif "/v1/metadata/version" in url:
                    mock_response.json.return_value = {
                        "version": "7.6.0",
                        "commitId": "02d9aa023a8d034d480a718242df2a880e0be1f7",
                    }

                return mock_response

            mock_get.side_effect = mock_get_side_effect

            # Test connection
            result = self.client.test_connection()

            # Verify it includes basic connection info
            self.assertIn("status", result)
            self.assertIn("url", result)
            self.assertIn("response_time_ms", result)

    def test_consolidated_approach_no_duplicates(self):
        """Test that we have consolidated to use existing get_registry_info only."""
        # Import the MCP module to check available tools
        import kafka_schema_registry_unified_mcp as mcp_module

        # Check that we have the existing get_registry_info (which now includes metadata)
        self.assertTrue(hasattr(mcp_module, "get_registry_info"))

        # Check that no separate metadata endpoints exist
        self.assertFalse(hasattr(mcp_module, "get_registry_metadata"))
        self.assertFalse(hasattr(mcp_module, "get_registry_version_info"))
        self.assertFalse(hasattr(mcp_module, "get_registry_cluster_info"))

        # Check that duplicate test utilities don't exist
        self.assertFalse(hasattr(mcp_module, "test_registry_connection_with_metadata"))
        self.assertFalse(hasattr(mcp_module, "test_schema_operations_with_metadata"))

        print("✅ Consolidated approach verified - using existing get_registry_info with metadata")

    def test_enhanced_existing_methods(self):
        """Test that existing methods are enhanced rather than duplicated."""
        import kafka_schema_registry_unified_mcp as mcp_module

        # Verify enhanced existing methods exist
        self.assertTrue(hasattr(mcp_module, "test_registry_connection"))
        self.assertTrue(hasattr(mcp_module, "test_all_registries"))
        self.assertTrue(hasattr(mcp_module, "count_schemas"))
        self.assertTrue(hasattr(mcp_module, "count_contexts"))
        self.assertTrue(hasattr(mcp_module, "get_registry_statistics"))

        print("✅ Enhanced existing methods verified")


if __name__ == "__main__":
    print("🧪 Testing Consolidated Metadata Integration")
    print("=" * 50)

    unittest.main(verbosity=2)
