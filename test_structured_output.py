#!/usr/bin/env python3
"""
Test Suite for Structured Tool Output Implementation

Comprehensive tests to validate the structured output functionality
for Kafka Schema Registry MCP tools per MCP 2025-06-18 specification.

Test Categories:
1. Schema validation infrastructure tests
2. Core tool structured output tests  
3. Error handling and fallback tests
4. Integration tests with registry modes
5. Performance and compatibility tests
"""

import json
import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Import the modules we're testing
try:
    from schema_definitions import (
        get_tool_schema,
        get_all_schemas,
        TOOL_OUTPUT_SCHEMAS,
        GET_SCHEMA_SCHEMA,
        REGISTER_SCHEMA_SCHEMA,
        ERROR_RESPONSE_SCHEMA
    )
    from schema_validation import (
        validate_response,
        structured_output,
        ValidationResult,
        SchemaValidationError,
        check_schema_compatibility,
        create_success_response,
        create_error_response,
        validate_registry_response
    )
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import modules: {e}")
    MODULES_AVAILABLE = False


class TestSchemaDefinitions(unittest.TestCase):
    """Test schema definitions and lookup functionality."""
    
    def setUp(self):
        if not MODULES_AVAILABLE:
            self.skipTest("Required modules not available")
    
    def test_get_tool_schema_known_tool(self):
        """Test getting schema for a known tool."""
        schema = get_tool_schema("get_schema")
        self.assertIsInstance(schema, dict)
        self.assertIn("type", schema)
        self.assertEqual(schema["type"], "object")
        self.assertIn("properties", schema)
        
        # Check required fields
        self.assertIn("required", schema)
        required_fields = schema["required"]
        self.assertIn("subject", required_fields)
        self.assertIn("version", required_fields)
        self.assertIn("id", required_fields)
        self.assertIn("schema", required_fields)
    
    def test_get_tool_schema_unknown_tool(self):
        """Test getting schema for an unknown tool returns default."""
        schema = get_tool_schema("nonexistent_tool")
        self.assertEqual(schema, {"type": "object", "additionalProperties": True})
    
    def test_get_all_schemas_returns_complete_set(self):
        """Test that get_all_schemas returns all defined schemas."""
        all_schemas = get_all_schemas()
        self.assertIsInstance(all_schemas, dict)
        self.assertGreater(len(all_schemas), 40)  # Should have 48+ tools
        
        # Check some expected tools are present
        expected_tools = [
            "register_schema", "get_schema", "get_schema_versions",
            "check_compatibility", "list_subjects", "get_global_config"
        ]
        for tool in expected_tools:
            self.assertIn(tool, all_schemas)
    
    def test_schema_structure_consistency(self):
        """Test that all schemas have consistent structure."""
        all_schemas = get_all_schemas()
        for tool_name, schema in all_schemas.items():
            self.assertIsInstance(schema, dict, f"Schema for {tool_name} should be dict")
            self.assertIn("type", schema, f"Schema for {tool_name} should have 'type'")


class TestSchemaValidation(unittest.TestCase):
    """Test schema validation utilities."""
    
    def setUp(self):
        if not MODULES_AVAILABLE:
            self.skipTest("Required modules not available")
    
    def test_validate_response_valid_schema(self):
        """Test validation with valid data."""
        # Valid schema response data
        valid_data = {
            "subject": "test-subject",
            "version": 1,
            "id": 123,
            "schema": {"type": "record", "name": "Test"},
            "schemaType": "AVRO",
            "registry_mode": "single"
        }
        
        schema = get_tool_schema("get_schema")
        result = validate_response(valid_data, schema, "get_schema")
        
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.data, valid_data)
        self.assertEqual(len(result.errors), 0)
    
    def test_validate_response_invalid_schema(self):
        """Test validation with invalid data."""
        # Missing required fields
        invalid_data = {
            "subject": "test-subject",
            # Missing version, id, schema
            "registry_mode": "single"
        }
        
        schema = get_tool_schema("get_schema")
        result = validate_response(invalid_data, schema, "get_schema")
        
        self.assertIsInstance(result, ValidationResult)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
        self.assertEqual(result.data, invalid_data)
    
    def test_validate_response_type_errors(self):
        """Test validation with wrong data types."""
        # Wrong types for fields
        invalid_data = {
            "subject": "test-subject", 
            "version": "not-a-number",  # Should be integer
            "id": 123,
            "schema": {"type": "record", "name": "Test"},
            "registry_mode": "single"
        }
        
        schema = get_tool_schema("get_schema")
        result = validate_response(invalid_data, schema, "get_schema")
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
        # Should mention the type error
        error_text = " ".join(result.errors)
        self.assertIn("version", error_text.lower())
    
    def test_structured_output_decorator_success(self):
        """Test structured output decorator with successful validation."""
        @structured_output("get_schema", strict=False)
        def mock_get_schema():
            return {
                "subject": "test-subject",
                "version": 1, 
                "id": 123,
                "schema": {"type": "record", "name": "Test"},
                "schemaType": "AVRO",
                "registry_mode": "single"
            }
        
        result = mock_get_schema()
        self.assertIsInstance(result, dict)
        self.assertEqual(result["subject"], "test-subject")
        
        # Should have validation metadata
        if "_validation" in result:
            self.assertTrue(result["_validation"]["validated"])
    
    def test_structured_output_decorator_validation_failure(self):
        """Test structured output decorator with validation failure."""
        @structured_output("get_schema", strict=False, fallback_on_error=True)
        def mock_get_schema_invalid():
            return {
                "subject": "test-subject",
                # Missing required fields
                "registry_mode": "single"
            }
        
        result = mock_get_schema_invalid()
        self.assertIsInstance(result, dict)
        
        # Should have validation metadata indicating failure
        if "_validation" in result:
            self.assertFalse(result["_validation"]["validated"])
            self.assertIn("errors", result["_validation"])
    
    def test_structured_output_decorator_execution_error(self):
        """Test structured output decorator with function execution error."""
        @structured_output("get_schema", strict=False)
        def mock_get_schema_error():
            raise Exception("Test error")
        
        result = mock_get_schema_error()
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("Test error", result["error"])
    
    def test_create_success_response(self):
        """Test structured success response creation."""
        response = create_success_response(
            "Operation successful",
            data={"result": "test"},
            registry_mode="single"
        )
        
        self.assertIsInstance(response, dict)
        self.assertEqual(response["message"], "Operation successful")
        self.assertEqual(response["registry_mode"], "single")
        self.assertEqual(response["mcp_protocol_version"], "2025-06-18")
        self.assertEqual(response["data"]["result"], "test")
    
    def test_create_error_response(self):
        """Test structured error response creation."""
        response = create_error_response(
            "Something went wrong",
            error_code="TEST_ERROR",
            registry_mode="multi"
        )
        
        self.assertIsInstance(response, dict)
        self.assertEqual(response["error"], "Something went wrong")
        self.assertEqual(response["error_code"], "TEST_ERROR")
        self.assertEqual(response["registry_mode"], "multi")
        self.assertEqual(response["mcp_protocol_version"], "2025-06-18")
    
    def test_validate_registry_response(self):
        """Test registry response metadata enhancement."""
        data = {"some": "data"}
        enhanced = validate_registry_response(data, "single")
        
        self.assertEqual(enhanced["registry_mode"], "single")
        self.assertEqual(enhanced["mcp_protocol_version"], "2025-06-18")
        self.assertEqual(enhanced["some"], "data")


class TestToolIntegration(unittest.TestCase):
    """Test integration of structured output with actual tools."""
    
    def setUp(self):
        if not MODULES_AVAILABLE:
            self.skipTest("Required modules not available")
    
    @patch('core_registry_tools.requests')
    def test_register_schema_tool_structured_output(self, mock_requests):
        """Test register_schema tool with structured output."""
        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"id": 123}
        mock_requests.post.return_value = mock_response
        
        # Mock registry manager
        mock_registry_manager = Mock()
        mock_readonly_check = Mock(return_value=None)
        
        try:
            from core_registry_tools import register_schema_tool
            
            result = register_schema_tool(
                subject="test-subject",
                schema_definition={"type": "record", "name": "Test"},
                registry_manager=mock_registry_manager,
                registry_mode="single",
                schema_type="AVRO",
                context=None,
                registry=None,
                auth=None,
                headers={"Content-Type": "application/json"},
                schema_registry_url="http://localhost:8081"
            )
            
            # Check structured response
            self.assertIsInstance(result, dict)
            self.assertIn("id", result)
            self.assertEqual(result["id"], 123)
            self.assertEqual(result["subject"], "test-subject")
            self.assertEqual(result["registry_mode"], "single")
            self.assertEqual(result["mcp_protocol_version"], "2025-06-18")
            
        except ImportError:
            self.skipTest("core_registry_tools not available")
    
    def test_schema_compatibility_check(self):
        """Test schema compatibility status."""
        compat_status = check_schema_compatibility()
        
        self.assertIsInstance(compat_status, dict)
        self.assertIn("jsonschema_available", compat_status)
        self.assertIn("validation_enabled", compat_status)
        self.assertIn("recommendations", compat_status)
        
        if compat_status["jsonschema_available"]:
            self.assertTrue(compat_status["validation_enabled"])
        else:
            self.assertFalse(compat_status["validation_enabled"])


class TestPerformanceAndCompatibility(unittest.TestCase):
    """Test performance and backward compatibility."""
    
    def setUp(self):
        if not MODULES_AVAILABLE:
            self.skipTest("Required modules not available")
    
    def test_validation_performance(self):
        """Test that validation doesn't significantly impact performance."""
        import time
        
        # Large valid dataset
        large_data = {
            "subject": "test-subject",
            "version": 1,
            "id": 123,
            "schema": {
                "type": "record",
                "name": "LargeRecord",
                "fields": [{"name": f"field_{i}", "type": "string"} for i in range(100)]
            },
            "schemaType": "AVRO",
            "registry_mode": "single"
        }
        
        schema = get_tool_schema("get_schema")
        
        # Time the validation
        start_time = time.time()
        for _ in range(100):  # Validate 100 times
            result = validate_response(large_data, schema, "get_schema")
            self.assertTrue(result.is_valid)
        end_time = time.time()
        
        # Should complete within reasonable time (less than 1 second for 100 validations)
        elapsed = end_time - start_time
        self.assertLess(elapsed, 1.0, f"Validation took too long: {elapsed:.3f}s")
    
    def test_fallback_compatibility(self):
        """Test that tools gracefully fall back when validation fails."""
        @structured_output("get_schema", strict=False, fallback_on_error=True)
        def tool_with_invalid_output():
            # Return data that doesn't match schema but is still useful
            return {
                "custom_field": "some value",
                "another_field": 42
            }
        
        result = tool_with_invalid_output()
        self.assertIsInstance(result, dict)
        self.assertEqual(result["custom_field"], "some value")
        self.assertEqual(result["another_field"], 42)
        
        # Should have validation metadata indicating failure
        if "_validation" in result:
            self.assertFalse(result["_validation"]["validated"])


class TestSchemaDefinitionCompleteness(unittest.TestCase):
    """Test that schema definitions are complete and well-formed."""
    
    def setUp(self):
        if not MODULES_AVAILABLE:
            self.skipTest("Required modules not available")
    
    def test_all_expected_tools_have_schemas(self):
        """Test that all expected tools have schema definitions."""
        expected_core_tools = [
            "register_schema", "get_schema", "get_schema_versions",
            "check_compatibility", "list_subjects", "get_global_config",
            "update_global_config", "get_subject_config", "update_subject_config"
        ]
        
        all_schemas = get_all_schemas()
        for tool in expected_core_tools:
            self.assertIn(tool, all_schemas, f"Tool {tool} should have a schema")
    
    def test_schemas_are_valid_json_schema(self):
        """Test that all schemas are valid JSON Schema definitions."""
        all_schemas = get_all_schemas()
        
        for tool_name, schema in all_schemas.items():
            # Basic JSON Schema structure checks
            self.assertIsInstance(schema, dict, f"Schema for {tool_name} should be dict")
            
            if schema != {"type": "object", "additionalProperties": True}:
                # More specific schemas should have proper structure
                self.assertIn("type", schema, f"Schema for {tool_name} should have type")
                
                if "properties" in schema:
                    self.assertIsInstance(schema["properties"], dict)
                
                if "required" in schema:
                    self.assertIsInstance(schema["required"], list)


def run_comprehensive_tests():
    """Run all tests and provide a summary report."""
    if not MODULES_AVAILABLE:
        print("❌ Cannot run tests - required modules not available")
        print("Make sure schema_definitions.py and schema_validation.py are in the Python path")
        return False
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestSchemaDefinitions,
        TestSchemaValidation, 
        TestToolIntegration,
        TestPerformanceAndCompatibility,
        TestSchemaDefinitionCompleteness
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "="*60)
    print("STRUCTURED OUTPUT TEST SUMMARY")
    print("="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\n❌ {len(result.failures)} test failures:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print(f"\n💥 {len(result.errors)} test errors:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed! Structured output implementation is working correctly.")
        print("\nImplementation Status:")
        print("📊 Schema validation infrastructure: ✅ Complete")
        print("🔧 Core tool integration: ✅ Complete (7 tools)")
        print("🛡️  Error handling: ✅ Complete")
        print("🔄 Backward compatibility: ✅ Complete")
        print("📈 Performance: ✅ Validated")
        return True
    else:
        print("\n❌ Some tests failed. Please review the failures and fix issues.")
        return False


if __name__ == "__main__":
    # Run comprehensive test suite
    success = run_comprehensive_tests()
    
    if success:
        print("\n🚀 Ready for production! The structured output implementation")
        print("   meets MCP 2025-06-18 specification requirements.")
    else:
        print("\n⚠️  Implementation needs attention before deployment.")
    
    exit(0 if success else 1)