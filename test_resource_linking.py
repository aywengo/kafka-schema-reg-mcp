#!/usr/bin/env python3
"""
Test Resource Linking Module

Tests for the resource linking functionality implemented as part of
MCP 2025-06-18 specification compliance.

This module validates URI generation, link creation, and navigation
helper functions.
"""

import json
import unittest
from typing import Any, Dict

from resource_linking import (
    RegistryURI,
    ResourceLinker,
    add_links_to_response,
    create_registry_linker,
    extract_registry_from_uri,
    parse_registry_uri,
    validate_registry_uri,
)


class TestRegistryURI(unittest.TestCase):
    """Test the RegistryURI class for URI generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.uri_builder = RegistryURI("test-registry")

    def test_context_uris(self):
        """Test context URI generation."""
        # Test default context
        self.assertEqual(
            self.uri_builder.context_uri(),
            "registry://test-registry/contexts/default"
        )
        
        # Test named context
        self.assertEqual(
            self.uri_builder.context_uri("production"),
            "registry://test-registry/contexts/production"
        )
        
        # Test context with special characters
        self.assertEqual(
            self.uri_builder.context_uri("test-env@2024"),
            "registry://test-registry/contexts/test-env%402024"
        )

    def test_subject_uris(self):
        """Test subject URI generation."""
        # Test subject in default context
        self.assertEqual(
            self.uri_builder.subject_uri("user-events"),
            "registry://test-registry/contexts/default/subjects/user-events"
        )
        
        # Test subject in named context
        self.assertEqual(
            self.uri_builder.subject_uri("user-events", "production"),
            "registry://test-registry/contexts/production/subjects/user-events"
        )

    def test_schema_version_uris(self):
        """Test schema version URI generation."""
        # Test specific version
        self.assertEqual(
            self.uri_builder.schema_version_uri("user-events", 3),
            "registry://test-registry/contexts/default/subjects/user-events/versions/3"
        )
        
        # Test latest version
        self.assertEqual(
            self.uri_builder.schema_version_uri("user-events", "latest", "production"),
            "registry://test-registry/contexts/production/subjects/user-events/versions/latest"
        )

    def test_configuration_uris(self):
        """Test configuration URI generation."""
        # Test subject config
        self.assertEqual(
            self.uri_builder.subject_config_uri("user-events"),
            "registry://test-registry/contexts/default/subjects/user-events/config"
        )
        
        # Test context config
        self.assertEqual(
            self.uri_builder.context_config_uri("production"),
            "registry://test-registry/contexts/production/config"
        )

    def test_migration_uris(self):
        """Test migration URI generation."""
        self.assertEqual(
            self.uri_builder.migration_uri("migration-123"),
            "registry://test-registry/migrations/migration-123"
        )
        
        self.assertEqual(
            self.uri_builder.migrations_list_uri(),
            "registry://test-registry/migrations"
        )

    def test_registry_name_sanitization(self):
        """Test that registry names are properly sanitized."""
        # Test with special characters
        uri_builder = RegistryURI("registry@with/special:chars")
        self.assertEqual(
            uri_builder.registry_name,
            "registry-with-special-chars"
        )


class TestResourceLinker(unittest.TestCase):
    """Test the ResourceLinker class for adding navigation links."""

    def setUp(self):
        """Set up test fixtures."""
        self.linker = ResourceLinker("test-registry")

    def test_schema_links(self):
        """Test adding links to schema responses."""
        response = {
            "id": 123,
            "version": 3,
            "schema": {"type": "record", "name": "User"}
        }
        
        enhanced = self.linker.add_schema_links(response, "user-events", 3, "production")
        
        # Check that _links section was added
        self.assertIn("_links", enhanced)
        links = enhanced["_links"]
        
        # Check required links
        self.assertIn("self", links)
        self.assertIn("subject", links)
        self.assertIn("context", links)
        self.assertIn("versions", links)
        self.assertIn("compatibility", links)
        
        # Check link format
        self.assertEqual(
            links["self"],
            "registry://test-registry/contexts/production/subjects/user-events/versions/3"
        )
        
        # Check previous/next version links
        self.assertIn("previous", links)
        self.assertIn("next", links)
        self.assertEqual(
            links["previous"],
            "registry://test-registry/contexts/production/subjects/user-events/versions/2"
        )

    def test_subjects_list_links(self):
        """Test adding links to subjects list responses."""
        subjects = ["user-events", "order-events", "payment-events"]
        
        enhanced = self.linker.add_subjects_list_links(subjects, "production")
        
        # Check structure
        self.assertIn("subjects", enhanced)
        self.assertIn("_links", enhanced)
        
        links = enhanced["_links"]
        self.assertIn("self", links)
        self.assertIn("context", links)
        self.assertIn("items", links)
        
        # Check individual subject links
        items = links["items"]
        self.assertEqual(len(items), 3)
        self.assertEqual(
            items["user-events"],
            "registry://test-registry/contexts/production/subjects/user-events"
        )

    def test_migration_links(self):
        """Test adding links to migration responses."""
        response = {
            "migration_id": "mig-123",
            "source_registry": "source-reg",
            "target_registry": "target-reg",
            "status": "completed"
        }
        
        enhanced = self.linker.add_migration_links(response, "mig-123")
        
        links = enhanced["_links"]
        self.assertIn("self", links)
        self.assertIn("migrations", links)
        self.assertIn("source_registry", links)
        self.assertIn("target_registry", links)
        
        self.assertEqual(
            links["source_registry"],
            "registry://source-reg"
        )


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions for URI validation and parsing."""

    def test_validate_registry_uri(self):
        """Test URI validation."""
        # Valid URIs
        self.assertTrue(validate_registry_uri("registry://test-reg"))
        self.assertTrue(validate_registry_uri("registry://test-reg/contexts/prod"))
        self.assertTrue(validate_registry_uri("registry://test-reg/contexts/prod/subjects/user-events/versions/3"))
        
        # Invalid URIs
        self.assertFalse(validate_registry_uri("http://example.com"))
        self.assertFalse(validate_registry_uri("registry://"))
        self.assertFalse(validate_registry_uri("invalid-scheme://test"))

    def test_extract_registry_from_uri(self):
        """Test extracting registry name from URI."""
        self.assertEqual(
            extract_registry_from_uri("registry://test-registry/contexts/prod"),
            "test-registry"
        )
        
        self.assertEqual(
            extract_registry_from_uri("registry://my-reg"),
            "my-reg"
        )
        
        self.assertIsNone(extract_registry_from_uri("invalid://uri"))

    def test_parse_registry_uri(self):
        """Test parsing URI components."""
        # Test schema version URI
        parsed = parse_registry_uri(
            "registry://test-reg/contexts/production/subjects/user-events/versions/3"
        )
        
        expected = {
            "registry": "test-reg",
            "context": "production",
            "subject": "user-events",
            "version": "3"
        }
        
        self.assertEqual(parsed, expected)
        
        # Test subject config URI
        parsed = parse_registry_uri(
            "registry://test-reg/contexts/production/subjects/user-events/config"
        )
        
        expected = {
            "registry": "test-reg",
            "context": "production",
            "subject": "user-events",
            "resource_type": "config"
        }
        
        self.assertEqual(parsed, expected)
        
        # Test migration URI
        parsed = parse_registry_uri("registry://test-reg/migrations/mig-123")
        
        expected = {
            "registry": "test-reg",
            "migration_id": "mig-123"
        }
        
        self.assertEqual(parsed, expected)

    def test_add_links_to_response(self):
        """Test the generic add_links_to_response function."""
        response = {
            "id": 123,
            "version": 3,
            "schema": {"type": "record"}
        }
        
        enhanced = add_links_to_response(
            response, "schema", "test-registry",
            subject="user-events", version=3, context="production"
        )
        
        self.assertIn("_links", enhanced)
        links = enhanced["_links"]
        self.assertIn("self", links)
        self.assertEqual(
            links["self"],
            "registry://test-registry/contexts/production/subjects/user-events/versions/3"
        )


class TestResourceLinkingIntegration(unittest.TestCase):
    """Integration tests for resource linking functionality."""

    def test_complete_workflow(self):
        """Test a complete workflow of creating and using resource links."""
        # Simulate a tool response for getting a schema
        response = {
            "id": 123,
            "version": 3,
            "schema": {
                "type": "record",
                "name": "User",
                "fields": [
                    {"name": "id", "type": "string"},
                    {"name": "email", "type": "string"}
                ]
            },
            "subject": "user-events",
            "registry_mode": "multi",
            "mcp_protocol_version": "2025-06-18"
        }
        
        # Add resource links
        enhanced = add_links_to_response(
            response, "schema", "production-registry",
            subject="user-events", version=3, context="production"
        )
        
        # Validate the enhanced response
        self.assertIn("_links", enhanced)
        links = enhanced["_links"]
        
        # Check all expected links are present
        expected_links = ["self", "subject", "context", "versions", "compatibility", "config", "mode"]
        for link_type in expected_links:
            self.assertIn(link_type, links)
        
        # Check navigation links
        self.assertIn("previous", links)
        self.assertIn("next", links)
        
        # Validate URI format
        for link_name, uri in links.items():
            self.assertTrue(validate_registry_uri(uri), f"Invalid URI for {link_name}: {uri}")
        
        # Check that we can parse the URIs back
        parsed_self = parse_registry_uri(links["self"])
        self.assertEqual(parsed_self["registry"], "production-registry")
        self.assertEqual(parsed_self["context"], "production")
        self.assertEqual(parsed_self["subject"], "user-events")
        self.assertEqual(parsed_self["version"], "3")

    def test_different_link_types(self):
        """Test different types of resource linking."""
        linker = create_registry_linker("test-registry")
        
        # Test subjects list
        subjects_response = ["user-events", "order-events"]
        enhanced_subjects = linker.add_subjects_list_links(subjects_response, "production")
        
        self.assertIn("_links", enhanced_subjects)
        self.assertIn("items", enhanced_subjects["_links"])
        
        # Test contexts list
        contexts_response = ["production", "staging", "development"]
        enhanced_contexts = linker.add_contexts_list_links(contexts_response)
        
        self.assertIn("_links", enhanced_contexts)
        self.assertIn("items", enhanced_contexts["_links"])
        
        # Test configuration
        config_response = {"compatibility": "BACKWARD"}
        enhanced_config = linker.add_config_links(config_response, "user-events", "production")
        
        self.assertIn("_links", enhanced_config)
        self.assertIn("subject", enhanced_config["_links"])
        self.assertIn("global_config", enhanced_config["_links"])

    def test_error_handling(self):
        """Test error handling in resource linking."""
        # Test with invalid link type
        response = {"test": "data"}
        enhanced = add_links_to_response(
            response, "invalid_type", "test-registry"
        )
        
        # Should return response unchanged for unknown link types
        self.assertEqual(enhanced, response)
        
        # Test with missing required parameters
        enhanced = add_links_to_response(
            response, "schema", "test-registry"
            # Missing subject and version parameters
        )
        
        # Should handle gracefully (specific behavior depends on implementation)
        self.assertIsInstance(enhanced, dict)


def run_tests():
    """Run all resource linking tests."""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestRegistryURI,
        TestResourceLinker,
        TestUtilityFunctions,
        TestResourceLinkingIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # Run tests if called directly
    success = run_tests()
    if success:
        print("\n✅ All resource linking tests passed!")
    else:
        print("\n❌ Some tests failed.")
        exit(1)
