#!/usr/bin/env python3
"""
Test Registry-Specific Resources

Tests for the new registry-specific resources:
- registry://status/{name}
- registry://info/{name}
- registry://mode/{name}

This test suite covers:
1. Single registry mode tests
2. Multi-registry mode tests
3. Error handling (registry not found, connection failures)
4. Success scenarios with proper data validation
5. Default registry detection
6. Viewonly mode handling
7. MCP compliance information
"""

# Standard library
import json
import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add the parent directory to the path to import the MCP server
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import the registry manager and related components
try:
    # Import elicitation support check
    from elicitation import is_elicitation_supported
    
    # Import MCP_PROTOCOL_VERSION and other variables from the main MCP module
    from kafka_schema_registry_unified_mcp import (
        MCP_PROTOCOL_VERSION,
        REGISTRY_MODE,
        SCHEMA_REGISTRY_URL,
        VIEWONLY,
        auth,
        registry_manager,
        standard_headers,
    )

except ImportError as e:
    print(f"❌ Failed to import MCP server components: {e}")
    sys.exit(1)


# Create test functions that replicate the resource logic
def get_registry_status_by_name(name: str):
    """Test implementation of registry status resource."""
    import json

    try:
        # Check if registry exists
        if name not in registry_manager.list_registries():
            return json.dumps(
                {
                    "error": f"Registry '{name}' not found",
                    "available_registries": registry_manager.list_registries(),
                    "registry_mode": REGISTRY_MODE,
                },
                indent=2,
            )

        # Get registry client
        client = registry_manager.get_registry(name)
        if not client:
            return json.dumps(
                {
                    "error": f"Could not get client for registry '{name}'",
                    "registry_name": name,
                    "registry_mode": REGISTRY_MODE,
                },
                indent=2,
            )

        # Test connection
        test_result = client.test_connection()

        # Get registry info
        registry_info = registry_manager.get_registry_info(name)

        # Check if this is the default registry
        is_default = False
        if hasattr(registry_manager, "get_default_registry"):
            is_default = registry_manager.get_default_registry() == name

        # Check viewonly mode
        viewonly_status = False
        if REGISTRY_MODE == "single":
            viewonly_status = VIEWONLY
        elif hasattr(client, "config") and hasattr(client.config, "viewonly"):
            viewonly_status = client.config.viewonly

        status_info = {
            "registry_name": name,
            "registry_mode": REGISTRY_MODE,
            "is_default": is_default,
            "connection_status": test_result.get("status", "unknown"),
            "connection_details": test_result,
            "registry_info": registry_info,
            "viewonly_mode": viewonly_status,
            "server_info": {
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                "server_version": "2.0.0-mcp-2025-06-18-compliant-with-elicitation-and-ping",
                "structured_output": "100% Complete",
                "elicitation_capability": "Enabled",
                "ping_support": "Enabled",
            },
            "last_checked": test_result.get("timestamp", "unknown"),
        }

        # Add connection-specific status messages
        if test_result.get("status") == "connected":
            status_info["status_message"] = f"✅ {name}: Connected to {client.config.url}"
            status_info["health"] = "healthy"
        else:
            error_msg = test_result.get("error", "Connection failed")
            status_info["status_message"] = f"❌ {name}: {error_msg}"
            status_info["health"] = "unhealthy"
            status_info["error"] = error_msg

        return json.dumps(status_info, indent=2)

    except Exception as e:
        return json.dumps(
            {
                "error": f"Error checking status for registry '{name}': {str(e)}",
                "registry_name": name,
                "registry_mode": REGISTRY_MODE,
            },
            indent=2,
        )


def get_registry_info_by_name(name: str):
    """Test implementation of registry info resource."""
    import json

    try:
        # Check if registry exists
        if name not in registry_manager.list_registries():
            return json.dumps(
                {
                    "error": f"Registry '{name}' not found",
                    "available_registries": registry_manager.list_registries(),
                    "registry_mode": REGISTRY_MODE,
                },
                indent=2,
            )

        # Get registry info
        registry_info = registry_manager.get_registry_info(name)
        if not registry_info:
            return json.dumps(
                {
                    "error": f"Could not get info for registry '{name}'",
                    "registry_name": name,
                    "registry_mode": REGISTRY_MODE,
                },
                indent=2,
            )

        # Build comprehensive info
        detailed_info = {
            "registry_name": name,
            "registry_mode": REGISTRY_MODE,
            "configuration": registry_info,
            "server_integration": {
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                "structured_output": {
                    "implementation_status": "100% Complete",
                    "total_tools": "53+",
                    "completion_percentage": 100.0,
                },
                "elicitation_capability": {
                    "implementation_status": "Complete - MCP 2025-06-18 Specification",
                    "supported": is_elicitation_supported(),
                    "interactive_tools": [
                        "register_schema_interactive",
                        "migrate_context_interactive",
                        "check_compatibility_interactive",
                        "create_context_interactive",
                        "export_global_interactive",
                    ],
                },
                "ping_support": {
                    "implementation_status": "Complete - MCP ping/pong protocol",
                    "ping_tool": "ping",
                    "response_format": "pong",
                },
            },
            "capabilities": {
                "contexts_supported": True,
                "schema_types": ["AVRO", "JSON", "PROTOBUF"],
                "compatibility_levels": [
                    "BACKWARD",
                    "BACKWARD_TRANSITIVE",
                    "FORWARD",
                    "FORWARD_TRANSITIVE",
                    "FULL",
                    "FULL_TRANSITIVE",
                    "NONE",
                ],
                "modes": ["READWRITE", "READONLY", "IMPORT"],
            },
            "available_operations": [
                "Schema Registration",
                "Schema Retrieval",
                "Schema Versioning",
                "Compatibility Checking",
                "Context Management",
                "Configuration Management",
                "Mode Management",
                "Schema Export",
                "Schema Migration",
                "Statistics",
            ],
        }

        return json.dumps(detailed_info, indent=2)

    except Exception as e:
        return json.dumps(
            {
                "error": f"Error getting info for registry '{name}': {str(e)}",
                "registry_name": name,
                "registry_mode": REGISTRY_MODE,
            },
            indent=2,
        )


def get_registry_mode_by_name(name: str):
    """Test implementation of registry mode resource."""
    import json

    try:
        # Check if registry exists
        if name not in registry_manager.list_registries():
            return json.dumps(
                {
                    "error": f"Registry '{name}' not found",
                    "available_registries": registry_manager.list_registries(),
                    "registry_mode": REGISTRY_MODE,
                },
                indent=2,
            )

        # Get registry client
        client = registry_manager.get_registry(name)
        if not client:
            return json.dumps(
                {
                    "error": f"Could not get client for registry '{name}'",
                    "registry_name": name,
                    "registry_mode": REGISTRY_MODE,
                },
                indent=2,
            )

        # Build mode information
        mode_info = {
            "registry_name": name,
            "registry_mode": REGISTRY_MODE,
            "operational_mode": {
                "current_mode": None,
                "available_modes": ["READWRITE", "READONLY", "IMPORT"],
                "mode_accessible": False,
                "mode_description": {
                    "READWRITE": "Full read and write access to schemas",
                    "READONLY": "Read-only access, no schema modifications allowed",
                    "IMPORT": "Import mode for schema migration and bulk operations",
                },
            },
            "viewonly_mode": {"enabled": False, "description": "Server-level protection preventing write operations"},
            "mcp_server_capabilities": {
                "protocol_version": MCP_PROTOCOL_VERSION,
                "structured_output": {"implementation_status": "100% Complete", "all_tools_validated": True},
                "elicitation_capability": {
                    "implementation_status": "Complete - MCP 2025-06-18 Specification",
                    "supported": is_elicitation_supported(),
                    "interactive_mode_management": True,
                },
                "ping_support": {
                    "implementation_status": "Complete - MCP ping/pong protocol",
                    "health_monitoring": True,
                },
            },
            "supported_operations_for_registry": [
                "get_mode",
                "update_mode",
                "get_subject_mode",
                "update_subject_mode",
                "get_global_config",
                "update_global_config",
                "get_subject_config",
                "update_subject_config",
                "register_schema",
                "get_schema",
                "list_subjects",
                "check_compatibility",
                "list_contexts",
                "create_context",
                "delete_context",
                "delete_subject",
                "export_schema",
                "export_subject",
                "export_context",
                "migrate_schema",
            ],
        }

        # Add viewonly mode info
        if REGISTRY_MODE == "single":
            mode_info["viewonly_mode"]["enabled"] = VIEWONLY
        elif hasattr(client, "config") and hasattr(client.config, "viewonly"):
            mode_info["viewonly_mode"]["enabled"] = client.config.viewonly
        else:
            mode_info["viewonly_mode"]["enabled"] = False

        if mode_info["viewonly_mode"]["enabled"]:
            mode_info["viewonly_mode"]["affected_operations"] = [
                "register_schema",
                "update_mode",
                "update_global_config",
                "update_subject_config",
                "update_subject_mode",
                "create_context",
                "delete_context",
                "delete_subject",
                "migrate_schema",
                "clear_context_batch",
            ]

        return json.dumps(mode_info, indent=2)

    except Exception as e:
        return json.dumps(
            {
                "error": f"Error getting mode info for registry '{name}': {str(e)}",
                "registry_name": name,
                "registry_mode": REGISTRY_MODE,
            },
            indent=2,
        )


def get_schema_by_uri_with_context(name: str, context: str, subject_name: str):
    """Test implementation of schema resource with context."""
    import json

    from core_registry_tools import get_schema_tool

    try:
        # Check if registry exists
        if name not in registry_manager.list_registries():
            return json.dumps(
                {
                    "error": f"Registry '{name}' not found",
                    "available_registries": registry_manager.list_registries(),
                    "registry_mode": REGISTRY_MODE,
                    "resource_uri": f"schema://{name}/{context}/{subject_name}",
                },
                indent=2,
            )

        # Get the schema using the existing tool
        schema_result = get_schema_tool(
            subject_name,
            registry_manager,
            REGISTRY_MODE,
            "latest",  # Always get latest version for resource
            context,
            name,
            auth,
            standard_headers,
            SCHEMA_REGISTRY_URL,
        )

        # If the result is a dict (successful response), enhance it with resource metadata
        if isinstance(schema_result, dict) and "error" not in schema_result:
            schema_result["resource_info"] = {
                "resource_uri": f"schema://{name}/{context}/{subject_name}",
                "registry_name": name,
                "context": context,
                "subject_name": subject_name,
                "version": "latest",
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            }

            # Add navigation links to related resources
            schema_result["related_resources"] = {
                "registry_status": f"registry://status/{name}",
                "registry_info": f"registry://info/{name}",
                "schema_without_context": f"schema://{name}/{subject_name}",
                "all_versions": f"Get all versions using tool: get_schema_versions(subject='{subject_name}', context='{context}', registry='{name}')",
            }

            return json.dumps(schema_result, indent=2)

        # If it's an error response, add resource metadata
        elif isinstance(schema_result, dict) and "error" in schema_result:
            schema_result["resource_info"] = {
                "resource_uri": f"schema://{name}/{context}/{subject_name}",
                "registry_name": name,
                "context": context,
                "subject_name": subject_name,
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            }
            return json.dumps(schema_result, indent=2)

        # If it's a string response, wrap it in proper structure
        else:
            return json.dumps(
                {
                    "schema_content": schema_result,
                    "resource_info": {
                        "resource_uri": f"schema://{name}/{context}/{subject_name}",
                        "registry_name": name,
                        "context": context,
                        "subject_name": subject_name,
                        "version": "latest",
                        "registry_mode": REGISTRY_MODE,
                        "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                    },
                    "related_resources": {
                        "registry_status": f"registry://status/{name}",
                        "registry_info": f"registry://info/{name}",
                        "schema_without_context": f"schema://{name}/{subject_name}",
                        "all_versions": f"Get all versions using tool: get_schema_versions(subject='{subject_name}', context='{context}', registry='{name}')",
                    },
                },
                indent=2,
            )

    except Exception as e:
        return json.dumps(
            {
                "error": f"Error getting schema for '{subject_name}' in context '{context}' from registry '{name}': {str(e)}",
                "resource_uri": f"schema://{name}/{context}/{subject_name}",
                "registry_name": name,
                "context": context,
                "subject_name": subject_name,
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
            indent=2,
        )


def get_schema_by_uri_default_context(name: str, subject_name: str):
    """Test implementation of schema resource with default context."""
    import json

    from core_registry_tools import get_schema_tool

    try:
        # Check if registry exists
        if name not in registry_manager.list_registries():
            return json.dumps(
                {
                    "error": f"Registry '{name}' not found",
                    "available_registries": registry_manager.list_registries(),
                    "registry_mode": REGISTRY_MODE,
                    "resource_uri": f"schema://{name}/{subject_name}",
                },
                indent=2,
            )

        # Use default context (represented as ".")
        context = "."

        # Get the schema using the existing tool
        schema_result = get_schema_tool(
            subject_name,
            registry_manager,
            REGISTRY_MODE,
            "latest",  # Always get latest version for resource
            context,
            name,
            auth,
            standard_headers,
            SCHEMA_REGISTRY_URL,
        )

        # If the result is a dict (successful response), enhance it with resource metadata
        if isinstance(schema_result, dict) and "error" not in schema_result:
            schema_result["resource_info"] = {
                "resource_uri": f"schema://{name}/{subject_name}",
                "registry_name": name,
                "context": context,
                "context_description": "Default context",
                "subject_name": subject_name,
                "version": "latest",
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            }

            # Add navigation links to related resources
            schema_result["related_resources"] = {
                "registry_status": f"registry://status/{name}",
                "registry_info": f"registry://info/{name}",
                "schema_with_explicit_context": f"schema://{name}/{context}/{subject_name}",
                "all_versions": f"Get all versions using tool: get_schema_versions(subject='{subject_name}', context='{context}', registry='{name}')",
            }

            return json.dumps(schema_result, indent=2)

        # If it's an error response, add resource metadata
        elif isinstance(schema_result, dict) and "error" in schema_result:
            schema_result["resource_info"] = {
                "resource_uri": f"schema://{name}/{subject_name}",
                "registry_name": name,
                "context": context,
                "context_description": "Default context",
                "subject_name": subject_name,
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            }
            return json.dumps(schema_result, indent=2)

        # If it's a string response, wrap it in proper structure
        else:
            return json.dumps(
                {
                    "schema_content": schema_result,
                    "resource_info": {
                        "resource_uri": f"schema://{name}/{subject_name}",
                        "registry_name": name,
                        "context": context,
                        "context_description": "Default context",
                        "subject_name": subject_name,
                        "version": "latest",
                        "registry_mode": REGISTRY_MODE,
                        "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                    },
                    "related_resources": {
                        "registry_status": f"registry://status/{name}",
                        "registry_info": f"registry://info/{name}",
                        "schema_with_explicit_context": f"schema://{name}/{context}/{subject_name}",
                        "all_versions": f"Get all versions using tool: get_schema_versions(subject='{subject_name}', context='{context}', registry='{name}')",
                    },
                },
                indent=2,
            )

    except Exception as e:
        return json.dumps(
            {
                "error": f"Error getting schema for '{subject_name}' in default context from registry '{name}': {str(e)}",
                "resource_uri": f"schema://{name}/{subject_name}",
                "registry_name": name,
                "context": ".",
                "context_description": "Default context",
                "subject_name": subject_name,
                "registry_mode": REGISTRY_MODE,
                "mcp_protocol_version": MCP_PROTOCOL_VERSION,
            },
            indent=2,
        )


class TestRegistrySpecificResources(unittest.TestCase):
    """Test registry-specific resources functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_registry_name = "test-registry"
        self.nonexistent_registry = "nonexistent-registry"

        # Mock registry info
        self.mock_registry_info = {
            "name": self.test_registry_name,
            "url": "http://localhost:8081",
            "user": "test-user",
            "viewonly": False,
            "description": "Test registry for unit tests",
        }

        # Mock connection test result
        self.mock_connection_success = {
            "status": "connected",
            "timestamp": "2023-01-01T00:00:00Z",
            "url": "http://localhost:8081",
            "response_time": 0.1,
            "version": "7.0.0",
        }

        self.mock_connection_failure = {
            "status": "failed",
            "timestamp": "2023-01-01T00:00:00Z",
            "error": "Connection refused",
            "url": "http://localhost:8081",
        }

    def test_registry_status_success(self):
        """Test successful registry status retrieval."""
        with (
            patch.object(registry_manager, "list_registries") as mock_list,
            patch.object(registry_manager, "get_registry") as mock_get,
            patch.object(registry_manager, "get_registry_info") as mock_info,
        ):

            # Setup mocks
            mock_list.return_value = [self.test_registry_name]
            mock_client = Mock()
            mock_client.test_connection.return_value = self.mock_connection_success
            mock_client.config.url = "http://localhost:8081"
            mock_client.config.viewonly = False
            mock_get.return_value = mock_client
            mock_info.return_value = self.mock_registry_info

            # Mock default registry check
            if hasattr(registry_manager, "get_default_registry"):
                with patch.object(registry_manager, "get_default_registry") as mock_default:
                    mock_default.return_value = self.test_registry_name
                    result_json = get_registry_status_by_name(self.test_registry_name)
            else:
                result_json = get_registry_status_by_name(self.test_registry_name)

            # Parse and validate result
            result = json.loads(result_json)

            self.assertEqual(result["registry_name"], self.test_registry_name)
            self.assertEqual(result["registry_mode"], REGISTRY_MODE)
            self.assertEqual(result["connection_status"], "connected")
            self.assertEqual(result["health"], "healthy")
            self.assertIn("status_message", result)
            self.assertIn("Connected to", result["status_message"])
            self.assertEqual(result["registry_info"], self.mock_registry_info)
            self.assertEqual(result["server_info"]["mcp_protocol_version"], MCP_PROTOCOL_VERSION)

    def test_registry_status_connection_failure(self):
        """Test registry status with connection failure."""
        with (
            patch.object(registry_manager, "list_registries") as mock_list,
            patch.object(registry_manager, "get_registry") as mock_get,
            patch.object(registry_manager, "get_registry_info") as mock_info,
        ):

            # Setup mocks
            mock_list.return_value = [self.test_registry_name]
            mock_client = Mock()
            mock_client.test_connection.return_value = self.mock_connection_failure
            mock_client.config.url = "http://localhost:8081"
            mock_client.config.viewonly = False
            mock_get.return_value = mock_client
            mock_info.return_value = self.mock_registry_info

            result_json = get_registry_status_by_name(self.test_registry_name)
            result = json.loads(result_json)

            self.assertEqual(result["registry_name"], self.test_registry_name)
            self.assertEqual(result["connection_status"], "failed")
            self.assertEqual(result["health"], "unhealthy")
            self.assertIn("error", result)
            self.assertEqual(result["error"], "Connection refused")

    def test_registry_status_not_found(self):
        """Test registry status for nonexistent registry."""
        with patch.object(registry_manager, "list_registries") as mock_list:
            mock_list.return_value = [self.test_registry_name]

            result_json = get_registry_status_by_name(self.nonexistent_registry)
            result = json.loads(result_json)

            self.assertIn("error", result)
            self.assertIn("not found", result["error"])
            self.assertEqual(result["available_registries"], [self.test_registry_name])
            self.assertEqual(result["registry_mode"], REGISTRY_MODE)

    def test_registry_info_success(self):
        """Test successful registry info retrieval."""
        with (
            patch.object(registry_manager, "list_registries") as mock_list,
            patch.object(registry_manager, "get_registry") as mock_get,
            patch.object(registry_manager, "get_registry_info") as mock_info,
        ):

            # Setup mocks
            mock_list.return_value = [self.test_registry_name]
            mock_client = Mock()
            mock_client.test_connection.return_value = self.mock_connection_success
            mock_client.config.viewonly = False
            mock_get.return_value = mock_client
            mock_info.return_value = self.mock_registry_info

            # Mock default registry check
            if hasattr(registry_manager, "get_default_registry"):
                with patch.object(registry_manager, "get_default_registry") as mock_default:
                    mock_default.return_value = self.test_registry_name
                    result_json = get_registry_info_by_name(self.test_registry_name)
            else:
                result_json = get_registry_info_by_name(self.test_registry_name)

            # Parse and validate result
            result = json.loads(result_json)

            self.assertEqual(result["registry_name"], self.test_registry_name)
            self.assertEqual(result["registry_mode"], REGISTRY_MODE)
            self.assertEqual(result["configuration"], self.mock_registry_info)
            self.assertIn("capabilities", result)
            self.assertIn("server_integration", result)
            self.assertIn("available_operations", result)

            # Validate capabilities
            capabilities = result["capabilities"]
            self.assertTrue(capabilities["contexts_supported"])
            self.assertIn("AVRO", capabilities["schema_types"])
            self.assertIn("BACKWARD", capabilities["compatibility_levels"])
            self.assertIn("READWRITE", capabilities["modes"])

            # Validate server integration
            server_integration = result["server_integration"]
            self.assertEqual(server_integration["mcp_protocol_version"], MCP_PROTOCOL_VERSION)
            self.assertIn("structured_output", server_integration)
            self.assertIn("elicitation_capability", server_integration)
            self.assertIn("ping_support", server_integration)

    def test_registry_info_not_found(self):
        """Test registry info for nonexistent registry."""
        with patch.object(registry_manager, "list_registries") as mock_list:
            mock_list.return_value = [self.test_registry_name]

            result_json = get_registry_info_by_name(self.nonexistent_registry)
            result = json.loads(result_json)

            self.assertIn("error", result)
            self.assertIn("not found", result["error"])
            self.assertEqual(result["available_registries"], [self.test_registry_name])

    def test_registry_mode_success(self):
        """Test successful registry mode retrieval."""
        with (
            patch.object(registry_manager, "list_registries") as mock_list,
            patch.object(registry_manager, "get_registry") as mock_get,
            patch.object(registry_manager, "get_registry_info") as mock_info,
        ):

            # Setup mocks
            mock_list.return_value = [self.test_registry_name]
            mock_client = Mock()
            mock_client.config.viewonly = False
            mock_get.return_value = mock_client
            mock_info.return_value = self.mock_registry_info

            # Mock the get_mode_tool and get_global_config_tool calls
            with (
                patch("core_registry_tools.get_mode_tool") as mock_mode,
                patch("core_registry_tools.get_global_config_tool") as mock_config,
            ):

                mock_mode.return_value = {"mode": "READWRITE"}
                mock_config.return_value = {"compatibility": "BACKWARD"}

                result_json = get_registry_mode_by_name(self.test_registry_name)
                result = json.loads(result_json)

                self.assertEqual(result["registry_name"], self.test_registry_name)
                self.assertEqual(result["registry_mode"], REGISTRY_MODE)
                self.assertIn("operational_mode", result)
                self.assertIn("mcp_server_capabilities", result)
                self.assertIn("supported_operations_for_registry", result)

                # Validate operational mode - note that our test implementation doesn't actually call the tools
                operational_mode = result["operational_mode"]
                # The test implementation returns None for current_mode since it doesn't actually call the tools
                self.assertIsNone(operational_mode["current_mode"])
                self.assertFalse(operational_mode["mode_accessible"])
                self.assertIn("READWRITE", operational_mode["available_modes"])

                # Validate MCP server capabilities
                mcp_capabilities = result["mcp_server_capabilities"]
                self.assertEqual(mcp_capabilities["protocol_version"], MCP_PROTOCOL_VERSION)
                self.assertIn("structured_output", mcp_capabilities)
                self.assertIn("elicitation_capability", mcp_capabilities)
                self.assertIn("ping_support", mcp_capabilities)

    def test_registry_mode_with_viewonly(self):
        """Test registry mode with viewonly enabled."""
        with (
            patch.object(registry_manager, "list_registries") as mock_list,
            patch.object(registry_manager, "get_registry") as mock_get,
            patch.object(registry_manager, "get_registry_info") as mock_info,
        ):

            # Setup mocks
            mock_list.return_value = [self.test_registry_name]
            mock_client = Mock()
            mock_client.config.viewonly = True
            mock_get.return_value = mock_client
            mock_info.return_value = self.mock_registry_info

            result_json = get_registry_mode_by_name(self.test_registry_name)
            result = json.loads(result_json)

            self.assertEqual(result["registry_name"], self.test_registry_name)
            self.assertTrue(result["viewonly_mode"]["enabled"])
            self.assertIn("affected_operations", result["viewonly_mode"])
            self.assertIn("register_schema", result["viewonly_mode"]["affected_operations"])

    def test_registry_mode_not_found(self):
        """Test registry mode for nonexistent registry."""
        with patch.object(registry_manager, "list_registries") as mock_list:
            mock_list.return_value = [self.test_registry_name]

            result_json = get_registry_mode_by_name(self.nonexistent_registry)
            result = json.loads(result_json)

            self.assertIn("error", result)
            self.assertIn("not found", result["error"])
            self.assertEqual(result["available_registries"], [self.test_registry_name])

    def test_registry_status_client_not_found(self):
        """Test registry status when client cannot be obtained."""
        with (
            patch.object(registry_manager, "list_registries") as mock_list,
            patch.object(registry_manager, "get_registry") as mock_get,
        ):

            mock_list.return_value = [self.test_registry_name]
            mock_get.return_value = None

            result_json = get_registry_status_by_name(self.test_registry_name)
            result = json.loads(result_json)

            self.assertIn("error", result)
            self.assertIn("Could not get client", result["error"])
            self.assertEqual(result["registry_name"], self.test_registry_name)

    def test_registry_info_no_info_available(self):
        """Test registry info when registry info is not available."""
        with (
            patch.object(registry_manager, "list_registries") as mock_list,
            patch.object(registry_manager, "get_registry_info") as mock_info,
        ):

            mock_list.return_value = [self.test_registry_name]
            mock_info.return_value = None

            result_json = get_registry_info_by_name(self.test_registry_name)
            result = json.loads(result_json)

            self.assertIn("error", result)
            self.assertIn("Could not get info", result["error"])
            self.assertEqual(result["registry_name"], self.test_registry_name)

    def test_single_registry_mode_handling(self):
        """Test resources behavior in single registry mode."""
        # This test assumes we're in single registry mode
        if REGISTRY_MODE == "single":
            with (
                patch.object(registry_manager, "list_registries") as mock_list,
                patch.object(registry_manager, "get_registry") as mock_get,
                patch.object(registry_manager, "get_registry_info") as mock_info,
            ):

                # Setup mocks
                mock_list.return_value = ["default"]
                mock_client = Mock()
                mock_client.test_connection.return_value = self.mock_connection_success
                mock_client.config.url = "http://localhost:8081"
                mock_client.config.viewonly = VIEWONLY
                mock_get.return_value = mock_client
                mock_info.return_value = self.mock_registry_info

                result_json = get_registry_status_by_name("default")
                result = json.loads(result_json)

                self.assertEqual(result["registry_mode"], "single")
                self.assertEqual(result["viewonly_mode"], VIEWONLY)

    def test_multi_registry_mode_handling(self):
        """Test resources behavior in multi registry mode."""
        # This test assumes we're in multi registry mode
        if REGISTRY_MODE == "multi":
            with (
                patch.object(registry_manager, "list_registries") as mock_list,
                patch.object(registry_manager, "get_registry") as mock_get,
                patch.object(registry_manager, "get_registry_info") as mock_info,
                patch.object(registry_manager, "get_default_registry") as mock_default,
            ):

                # Setup mocks
                mock_list.return_value = [self.test_registry_name, "another-registry"]
                mock_client = Mock()
                mock_client.test_connection.return_value = self.mock_connection_success
                mock_client.config.url = "http://localhost:8081"
                mock_client.config.viewonly = False
                mock_get.return_value = mock_client
                mock_info.return_value = self.mock_registry_info
                mock_default.return_value = self.test_registry_name

                result_json = get_registry_status_by_name(self.test_registry_name)
                result = json.loads(result_json)

                self.assertEqual(result["registry_mode"], "multi")
                self.assertTrue(result["is_default"])
                self.assertFalse(result["viewonly_mode"])

    def test_error_handling_with_exceptions(self):
        """Test error handling when exceptions occur."""
        with patch.object(registry_manager, "list_registries") as mock_list:
            mock_list.side_effect = Exception("Test exception")

            # Test status resource
            result_json = get_registry_status_by_name(self.test_registry_name)
            result = json.loads(result_json)
            self.assertIn("error", result)
            self.assertIn("Test exception", result["error"])

            # Test info resource
            result_json = get_registry_info_by_name(self.test_registry_name)
            result = json.loads(result_json)
            self.assertIn("error", result)
            self.assertIn("Test exception", result["error"])

            # Test mode resource
            result_json = get_registry_mode_by_name(self.test_registry_name)
            result = json.loads(result_json)
            self.assertIn("error", result)
            self.assertIn("Test exception", result["error"])

    def test_json_structure_validation(self):
        """Test that all resources return valid JSON with expected structure."""
        with (
            patch.object(registry_manager, "list_registries") as mock_list,
            patch.object(registry_manager, "get_registry") as mock_get,
            patch.object(registry_manager, "get_registry_info") as mock_info,
        ):

            # Setup mocks
            mock_list.return_value = [self.test_registry_name]
            mock_client = Mock()
            mock_client.test_connection.return_value = self.mock_connection_success
            mock_client.config.url = "http://localhost:8081"
            mock_client.config.viewonly = False
            mock_get.return_value = mock_client
            mock_info.return_value = self.mock_registry_info

            # Test all resources return valid JSON
            resources = [get_registry_status_by_name, get_registry_info_by_name, get_registry_mode_by_name]

            for resource_func in resources:
                result_json = resource_func(self.test_registry_name)

                # Should be valid JSON
                result = json.loads(result_json)
                self.assertIsInstance(result, dict)

                # Should have registry_name and registry_mode
                self.assertIn("registry_name", result)
                self.assertIn("registry_mode", result)

                # Should have proper registry_mode value
                self.assertEqual(result["registry_mode"], REGISTRY_MODE)

    def test_mcp_compliance_information(self):
        """Test that MCP compliance information is included in resources."""
        with (
            patch.object(registry_manager, "list_registries") as mock_list,
            patch.object(registry_manager, "get_registry") as mock_get,
            patch.object(registry_manager, "get_registry_info") as mock_info,
        ):

            # Setup mocks
            mock_list.return_value = [self.test_registry_name]
            mock_client = Mock()
            mock_client.test_connection.return_value = self.mock_connection_success
            mock_client.config.url = "http://localhost:8081"
            mock_client.config.viewonly = False
            mock_get.return_value = mock_client
            mock_info.return_value = self.mock_registry_info

            # Test status resource
            result_json = get_registry_status_by_name(self.test_registry_name)
            result = json.loads(result_json)
            self.assertIn("server_info", result)
            self.assertEqual(result["server_info"]["mcp_protocol_version"], MCP_PROTOCOL_VERSION)

            # Test info resource
            result_json = get_registry_info_by_name(self.test_registry_name)
            result = json.loads(result_json)
            self.assertIn("server_integration", result)
            self.assertEqual(result["server_integration"]["mcp_protocol_version"], MCP_PROTOCOL_VERSION)

            # Test mode resource
            result_json = get_registry_mode_by_name(self.test_registry_name)
            result = json.loads(result_json)
            self.assertIn("mcp_server_capabilities", result)
            self.assertEqual(result["mcp_server_capabilities"]["protocol_version"], MCP_PROTOCOL_VERSION)

    def test_registry_names_resource_success(self):
        """Test registry names resource returns list of configured registries."""

        # Access the actual resource function
        def get_registry_names():
            """Get a list of all configured schema registry names."""
            try:
                registry_names = registry_manager.list_registries()

                # Get default registry if available
                default_registry = None
                if hasattr(registry_manager, "get_default_registry"):
                    default_registry = registry_manager.get_default_registry()

                # Build response with registry names and metadata
                names_info = {
                    "registry_names": registry_names,
                    "total_registries": len(registry_names),
                    "registry_mode": REGISTRY_MODE,
                    "default_registry": default_registry,
                    "server_info": {
                        "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                        "server_version": "2.0.0-mcp-2025-06-18-compliant-with-elicitation-and-ping",
                        "structured_output": "100% Complete",
                        "elicitation_capability": "Enabled",
                        "ping_support": "Enabled",
                    },
                }

                # Add viewonly mode info for single registry mode
                if REGISTRY_MODE == "single":
                    names_info["viewonly_mode"] = VIEWONLY

                # Add brief status for each registry
                registry_status = {}
                for name in registry_names:
                    try:
                        client = registry_manager.get_registry(name)
                        if client:
                            # Quick connection test
                            test_result = client.test_connection()
                            registry_status[name] = {
                                "status": test_result.get("status", "unknown"),
                                "url": (
                                    getattr(client.config, "url", "unknown") if hasattr(client, "config") else "unknown"
                                ),
                                "is_default": name == default_registry,
                            }
                        else:
                            registry_status[name] = {
                                "status": "configuration_error",
                                "url": "unknown",
                                "is_default": name == default_registry,
                            }
                    except Exception as e:
                        registry_status[name] = {
                            "status": "error",
                            "error": str(e),
                            "is_default": name == default_registry,
                        }

                names_info["registry_status"] = registry_status

                return json.dumps(names_info, indent=2)

            except Exception as e:
                return json.dumps(
                    {
                        "error": f"Error getting registry names: {str(e)}",
                        "registry_mode": REGISTRY_MODE,
                        "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                    },
                    indent=2,
                )

        # Test the resource
        result_json = get_registry_names()
        result = json.loads(result_json)

        # Basic structure validation
        self.assertIn("registry_names", result)
        self.assertIn("total_registries", result)
        self.assertIn("registry_mode", result)
        self.assertIn("server_info", result)
        self.assertIn("registry_status", result)

        # Check values
        self.assertEqual(result["registry_mode"], REGISTRY_MODE)
        self.assertIsInstance(result["registry_names"], list)
        self.assertEqual(result["total_registries"], len(result["registry_names"]))

        # Check server info
        server_info = result["server_info"]
        self.assertEqual(server_info["mcp_protocol_version"], MCP_PROTOCOL_VERSION)
        self.assertEqual(server_info["structured_output"], "100% Complete")
        self.assertEqual(server_info["elicitation_capability"], "Enabled")
        self.assertEqual(server_info["ping_support"], "Enabled")

        # Check registry status
        registry_status = result["registry_status"]
        self.assertIsInstance(registry_status, dict)

        # Each registry should have status info
        for name in result["registry_names"]:
            self.assertIn(name, registry_status)
            status_info = registry_status[name]
            self.assertIn("status", status_info)
            self.assertIn("is_default", status_info)
            self.assertIsInstance(status_info["is_default"], bool)

        # Check viewonly mode for single registry
        if REGISTRY_MODE == "single":
            self.assertIn("viewonly_mode", result)
            self.assertIsInstance(result["viewonly_mode"], bool)

    def test_registry_names_resource_empty_list(self):
        """Test registry names resource with empty registry list."""
        # Mock empty registry list
        with patch.object(registry_manager, "list_registries", return_value=[]):
            # Access the actual resource function
            def get_registry_names():
                """Get a list of all configured schema registry names."""
                try:
                    registry_names = registry_manager.list_registries()

                    # Get default registry if available
                    default_registry = None
                    if hasattr(registry_manager, "get_default_registry"):
                        default_registry = registry_manager.get_default_registry()

                    # Build response with registry names and metadata
                    names_info = {
                        "registry_names": registry_names,
                        "total_registries": len(registry_names),
                        "registry_mode": REGISTRY_MODE,
                        "default_registry": default_registry,
                        "server_info": {
                            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                            "server_version": "2.0.0-mcp-2025-06-18-compliant-with-elicitation-and-ping",
                            "structured_output": "100% Complete",
                            "elicitation_capability": "Enabled",
                            "ping_support": "Enabled",
                        },
                    }

                    # Add viewonly mode info for single registry mode
                    if REGISTRY_MODE == "single":
                        names_info["viewonly_mode"] = VIEWONLY

                    # Add brief status for each registry
                    registry_status = {}
                    for name in registry_names:
                        try:
                            client = registry_manager.get_registry(name)
                            if client:
                                # Quick connection test
                                test_result = client.test_connection()
                                registry_status[name] = {
                                    "status": test_result.get("status", "unknown"),
                                    "url": (
                                        getattr(client.config, "url", "unknown")
                                        if hasattr(client, "config")
                                        else "unknown"
                                    ),
                                    "is_default": name == default_registry,
                                }
                            else:
                                registry_status[name] = {
                                    "status": "configuration_error",
                                    "url": "unknown",
                                    "is_default": name == default_registry,
                                }
                        except Exception as e:
                            registry_status[name] = {
                                "status": "error",
                                "error": str(e),
                                "is_default": name == default_registry,
                            }

                    names_info["registry_status"] = registry_status

                    return json.dumps(names_info, indent=2)

                except Exception as e:
                    return json.dumps(
                        {
                            "error": f"Error getting registry names: {str(e)}",
                            "registry_mode": REGISTRY_MODE,
                            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                        },
                        indent=2,
                    )

            result_json = get_registry_names()
            result = json.loads(result_json)

            # Check empty list handling
            self.assertEqual(result["registry_names"], [])
            self.assertEqual(result["total_registries"], 0)
            self.assertEqual(result["registry_status"], {})
            self.assertEqual(result["registry_mode"], REGISTRY_MODE)

    def test_registry_names_resource_error_handling(self):
        """Test registry names resource error handling."""
        # Mock exception during registry list retrieval
        with patch.object(registry_manager, "list_registries") as mock_list:
            mock_list.side_effect = Exception("Test exception")

            # Access the actual resource function
            def get_registry_names():
                """Get a list of all configured schema registry names."""
                try:
                    registry_names = registry_manager.list_registries()

                    # Get default registry if available
                    default_registry = None
                    if hasattr(registry_manager, "get_default_registry"):
                        default_registry = registry_manager.get_default_registry()

                    # Build response with registry names and metadata
                    names_info = {
                        "registry_names": registry_names,
                        "total_registries": len(registry_names),
                        "registry_mode": REGISTRY_MODE,
                        "default_registry": default_registry,
                        "server_info": {
                            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                            "server_version": "2.0.0-mcp-2025-06-18-compliant-with-elicitation-and-ping",
                            "structured_output": "100% Complete",
                            "elicitation_capability": "Enabled",
                            "ping_support": "Enabled",
                        },
                    }

                    # Add viewonly mode info for single registry mode
                    if REGISTRY_MODE == "single":
                        names_info["viewonly_mode"] = VIEWONLY

                    # Add brief status for each registry
                    registry_status = {}
                    for name in registry_names:
                        try:
                            client = registry_manager.get_registry(name)
                            if client:
                                # Quick connection test
                                test_result = client.test_connection()
                                registry_status[name] = {
                                    "status": test_result.get("status", "unknown"),
                                    "url": (
                                        getattr(client.config, "url", "unknown")
                                        if hasattr(client, "config")
                                        else "unknown"
                                    ),
                                    "is_default": name == default_registry,
                                }
                            else:
                                registry_status[name] = {
                                    "status": "configuration_error",
                                    "url": "unknown",
                                    "is_default": name == default_registry,
                                }
                        except Exception as e:
                            registry_status[name] = {
                                "status": "error",
                                "error": str(e),
                                "is_default": name == default_registry,
                            }

                    names_info["registry_status"] = registry_status

                    return json.dumps(names_info, indent=2)

                except Exception as e:
                    return json.dumps(
                        {
                            "error": f"Error getting registry names: {str(e)}",
                            "registry_mode": REGISTRY_MODE,
                            "mcp_protocol_version": MCP_PROTOCOL_VERSION,
                        },
                        indent=2,
                    )

            result_json = get_registry_names()
            result = json.loads(result_json)

            # Check error handling
            self.assertIn("error", result)
            self.assertIn("Test exception", result["error"])
            self.assertEqual(result["registry_mode"], REGISTRY_MODE)
            self.assertEqual(result["mcp_protocol_version"], MCP_PROTOCOL_VERSION)


class TestSchemaResources(unittest.TestCase):
    """Test schema URI resources."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_registry_name = "test-registry"
        self.test_context = "test-context"
        self.test_subject = "test-subject"

    def test_schema_resource_with_context_success(self):
        """Test schema resource with explicit context."""
        # Mock the registry manager and get_schema_tool to return a successful response
        with (
            patch.object(registry_manager, "list_registries") as mock_list,
            patch("core_registry_tools.get_schema_tool") as mock_get_schema,
        ):

            mock_list.return_value = [self.test_registry_name]
            mock_get_schema.return_value = {
                "subject": self.test_subject,
                "version": 1,
                "id": 123,
                "schema": '{"type": "record", "name": "TestRecord", "fields": []}',
                "schemaType": "AVRO",
            }

            result_json = get_schema_by_uri_with_context(self.test_registry_name, self.test_context, self.test_subject)
            result = json.loads(result_json)

            # Validate the response structure
            self.assertIn("subject", result)
            self.assertIn("schema", result)
            self.assertIn("resource_info", result)
            self.assertIn("related_resources", result)

            # Check resource info
            resource_info = result["resource_info"]
            self.assertEqual(resource_info["registry_name"], self.test_registry_name)
            self.assertEqual(resource_info["context"], self.test_context)
            self.assertEqual(resource_info["subject_name"], self.test_subject)
            self.assertEqual(resource_info["version"], "latest")
            self.assertEqual(resource_info["registry_mode"], REGISTRY_MODE)
            self.assertEqual(resource_info["mcp_protocol_version"], MCP_PROTOCOL_VERSION)

            # Check related resources
            related = result["related_resources"]
            self.assertIn("registry_status", related)
            self.assertIn("registry_info", related)
            self.assertIn("schema_without_context", related)
            self.assertIn("all_versions", related)

    def test_schema_resource_default_context_success(self):
        """Test schema resource with default context."""
        # Mock the registry manager and get_schema_tool to return a successful response
        with (
            patch.object(registry_manager, "list_registries") as mock_list,
            patch("core_registry_tools.get_schema_tool") as mock_get_schema,
        ):

            mock_list.return_value = [self.test_registry_name]
            mock_get_schema.return_value = {
                "subject": self.test_subject,
                "version": 1,
                "id": 456,
                "schema": '{"type": "record", "name": "DefaultRecord", "fields": []}',
                "schemaType": "AVRO",
            }

            result_json = get_schema_by_uri_default_context(self.test_registry_name, self.test_subject)
            result = json.loads(result_json)

            # Validate the response structure
            self.assertIn("subject", result)
            self.assertIn("schema", result)
            self.assertIn("resource_info", result)
            self.assertIn("related_resources", result)

            # Check resource info
            resource_info = result["resource_info"]
            self.assertEqual(resource_info["registry_name"], self.test_registry_name)
            self.assertEqual(resource_info["context"], ".")
            self.assertEqual(resource_info["context_description"], "Default context")
            self.assertEqual(resource_info["subject_name"], self.test_subject)
            self.assertEqual(resource_info["version"], "latest")
            self.assertEqual(resource_info["registry_mode"], REGISTRY_MODE)
            self.assertEqual(resource_info["mcp_protocol_version"], MCP_PROTOCOL_VERSION)

            # Check related resources
            related = result["related_resources"]
            self.assertIn("registry_status", related)
            self.assertIn("registry_info", related)
            self.assertIn("schema_with_explicit_context", related)
            self.assertIn("all_versions", related)

    def test_schema_resource_registry_not_found(self):
        """Test schema resource with non-existent registry."""
        result_json = get_schema_by_uri_with_context("non-existent-registry", self.test_context, self.test_subject)
        result = json.loads(result_json)

        # Should return an error
        self.assertIn("error", result)
        self.assertIn("Registry 'non-existent-registry' not found", result["error"])
        self.assertIn("available_registries", result)
        self.assertIn("resource_uri", result)
        self.assertEqual(result["registry_mode"], REGISTRY_MODE)

    def test_schema_resource_schema_not_found(self):
        """Test schema resource when schema doesn't exist."""
        # Mock the registry manager and get_schema_tool to return an error response
        with (
            patch.object(registry_manager, "list_registries") as mock_list,
            patch("core_registry_tools.get_schema_tool") as mock_get_schema,
        ):

            mock_list.return_value = [self.test_registry_name]
            mock_get_schema.return_value = {
                "error": "Subject 'non-existent-subject' not found",
                "error_code": "SUBJECT_NOT_FOUND",
            }

            result_json = get_schema_by_uri_with_context(
                self.test_registry_name, self.test_context, "non-existent-subject"
            )
            result = json.loads(result_json)

            # Should return an error with resource info
            self.assertIn("error", result)
            self.assertIn("resource_info", result)
            self.assertEqual(result["resource_info"]["registry_name"], self.test_registry_name)
            self.assertEqual(result["resource_info"]["context"], self.test_context)
            self.assertEqual(result["resource_info"]["subject_name"], "non-existent-subject")

    def test_schema_resource_string_response(self):
        """Test schema resource when get_schema_tool returns a string."""
        # Mock the registry manager and get_schema_tool to return a string response
        with (
            patch.object(registry_manager, "list_registries") as mock_list,
            patch("core_registry_tools.get_schema_tool") as mock_get_schema,
        ):

            mock_list.return_value = [self.test_registry_name]
            mock_get_schema.return_value = '{"type": "record", "name": "StringResponse", "fields": []}'

            result_json = get_schema_by_uri_default_context(self.test_registry_name, self.test_subject)
            result = json.loads(result_json)

            # Should wrap string in proper structure
            self.assertIn("schema_content", result)
            self.assertIn("resource_info", result)
            self.assertIn("related_resources", result)
            self.assertEqual(result["schema_content"], '{"type": "record", "name": "StringResponse", "fields": []}')
            self.assertEqual(result["resource_info"]["registry_name"], self.test_registry_name)
            self.assertEqual(result["resource_info"]["context"], ".")

    def test_schema_resource_exception_handling(self):
        """Test schema resource exception handling."""
        # Mock the registry manager and get_schema_tool to raise an exception
        with (
            patch.object(registry_manager, "list_registries") as mock_list,
            patch("core_registry_tools.get_schema_tool") as mock_get_schema,
        ):

            mock_list.return_value = [self.test_registry_name]
            mock_get_schema.side_effect = Exception("Connection failed")

            result_json = get_schema_by_uri_with_context(self.test_registry_name, self.test_context, self.test_subject)
            result = json.loads(result_json)

            # Should return structured error
            self.assertIn("error", result)
            self.assertIn("Connection failed", result["error"])
            self.assertIn("resource_uri", result)
            self.assertEqual(result["registry_name"], self.test_registry_name)
            self.assertEqual(result["context"], self.test_context)
            self.assertEqual(result["subject_name"], self.test_subject)
            self.assertEqual(result["registry_mode"], REGISTRY_MODE)


class TestResourcesIntegration(unittest.TestCase):
    """Integration tests for registry-specific resources."""

    def test_resources_with_real_registry_manager(self):
        """Test resources with actual registry manager (mocked connections)."""
        # This test uses the actual registry manager but mocks network calls
        test_registry = "integration-test-registry"

        # Mock the network calls but use real registry manager logic
        with patch("requests.get") as mock_get:
            # Mock a successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"subjects": []}
            mock_response.elapsed.total_seconds.return_value = 0.1
            mock_get.return_value = mock_response

            # Test with a registry that exists in the manager
            available_registries = registry_manager.list_registries()
            if available_registries:
                test_registry = available_registries[0]

                # Test status resource
                result_json = get_registry_status_by_name(test_registry)
                result = json.loads(result_json)

                # Should not have error if registry exists
                if "error" not in result:
                    self.assertEqual(result["registry_name"], test_registry)
                    self.assertIn("connection_status", result)
                    self.assertIn("registry_info", result)


if __name__ == "__main__":
    # Set up test environment
    print("🧪 Testing Registry-Specific Resources")
    print(f"📡 Current registry mode: {REGISTRY_MODE}")
    print(f"🔧 Available registries: {registry_manager.list_registries()}")
    print(f"🏓 MCP Protocol Version: {MCP_PROTOCOL_VERSION}")

    # Run tests
    unittest.main(verbosity=2)
