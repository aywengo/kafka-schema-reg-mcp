#!/usr/bin/env python3
"""
Registry Management Tools Module - Updated with Resource Linking

Handles registry management operations with structured tool output
support per MCP 2025-06-18 specification including resource linking.

Provides registry listing, connection testing, and information retrieval
with JSON Schema validation, type-safe responses, and HATEOAS navigation links.
"""

from typing import Any, Dict, Optional

from resource_linking import add_links_to_response
from schema_validation import (
    create_error_response,
    structured_output,
)


def _get_registry_name_for_linking(registry_mode: str, registry_name: Optional[str] = None) -> str:
    """Helper function to get registry name for linking."""
    if registry_mode == "single":
        return "default"
    elif registry_name:
        return registry_name
    else:
        return "unknown"


@structured_output("list_registries", fallback_on_error=True)
def list_registries_tool(registry_manager, registry_mode: str) -> Dict[str, Any]:
    """
    List all configured Schema Registry instances with structured validation and resource links.

    Args:
        registry_manager: The registry manager instance
        registry_mode: Current registry mode (single/multi)

    Returns:
        Dictionary containing registry information with structured validation and navigation links
    """
    try:
        registries_list = []
        for name in registry_manager.list_registries():
            info = registry_manager.get_registry_info(name)
            if info:
                # Add structured output metadata
                info["registry_mode"] = registry_mode
                info["mcp_protocol_version"] = "2025-06-18"

                # Add resource links for each registry
                info = add_links_to_response(info, "registry", name)

                registries_list.append(info)

        # Convert to enhanced response format
        result = {
            "registries": registries_list,
            "total_count": len(registries_list),
            "registry_mode": registry_mode,
            "mcp_protocol_version": "2025-06-18",
        }

        # If no registries found, add helpful message
        if not registries_list:
            result["message"] = "No registries configured"
            result["help"] = {
                "single_mode": "Set SCHEMA_REGISTRY_URL environment variable",
                "multi_mode": "Set SCHEMA_REGISTRY_NAME_1, SCHEMA_REGISTRY_URL_1 environment variables",
            }

        # Add default registry information
        default_registry = registry_manager.get_default_registry()
        if default_registry:
            result["default_registry"] = default_registry

        return result
    except Exception as e:
        return create_error_response(str(e), error_code="REGISTRY_LIST_FAILED", registry_mode=registry_mode)


@structured_output("get_registry_info", fallback_on_error=True)
def get_registry_info_tool(registry_manager, registry_mode: str, registry: Optional[str] = None) -> Dict[str, Any]:
    """
    Get detailed information about a specific registry with structured validation and resource links.

    Args:
        registry_manager: The registry manager instance
        registry_mode: Current registry mode (single/multi)
        registry: Optional registry name

    Returns:
        Dictionary containing detailed registry information with structured validation and navigation links
    """
    try:
        if registry_mode == "single" and not registry:
            registry = registry_manager.get_default_registry()

        info = registry_manager.get_registry_info(registry)
        if info is None:
            return create_error_response(
                f"Registry '{registry}' not found",
                error_code="REGISTRY_NOT_FOUND",
                registry_mode=registry_mode,
            )

        # Add structured output metadata
        info["registry_mode"] = registry_mode
        info["mcp_protocol_version"] = "2025-06-18"

        # Add additional metadata for better context
        info["_metadata"] = {
            "queried_registry": registry,
            "is_default": registry == registry_manager.get_default_registry(),
            "query_timestamp": __import__("datetime").datetime.now().isoformat(),
        }

        # Add resource links
        registry_name_for_linking = _get_registry_name_for_linking(registry_mode, registry)
        info = add_links_to_response(info, "registry", registry_name_for_linking)

        return info
    except Exception as e:
        return create_error_response(str(e), error_code="REGISTRY_INFO_FAILED", registry_mode=registry_mode)


@structured_output("test_registry_connection", fallback_on_error=True)
def test_registry_connection_tool(
    registry_manager, registry_mode: str, registry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Test connection to a specific registry with comprehensive information including metadata and resource links.

    Args:
        registry_manager: The registry manager instance
        registry_mode: Current registry mode (single/multi)
        registry: Optional registry name

    Returns:
        Dictionary containing connection test results with structured validation and navigation links
    """
    try:
        if registry_mode == "single" and not registry:
            registry = registry_manager.get_default_registry()

        client = registry_manager.get_registry(registry)
        if client is None:
            return create_error_response(
                f"Registry '{registry}' not found",
                error_code="REGISTRY_NOT_FOUND",
                registry_mode=registry_mode,
            )

        # Get connection test result
        result = client.test_connection()

        # Add structured output metadata
        result["registry_mode"] = registry_mode
        result["mcp_protocol_version"] = "2025-06-18"
        result["test_timestamp"] = __import__("datetime").datetime.now().isoformat()

        # Add comprehensive metadata
        try:
            metadata = client.get_server_metadata()
            result["server_metadata"] = metadata
        except Exception as e:
            result["metadata_error"] = str(e)
            result["metadata_status"] = "failed"

        # Add registry configuration info (without sensitive data)
        result["registry_config"] = {
            "name": client.config.name,
            "url": client.config.url,
            "description": client.config.description,
            "viewonly": client.config.readonly,
            "has_authentication": bool(client.config.user and client.config.password),
        }

        # Add connection health assessment
        result["health_assessment"] = {
            "status": "healthy" if result.get("status") == "connected" else "unhealthy",
            "can_perform_operations": result.get("status") == "connected" and not client.config.readonly,
            "viewonly_mode": client.config.readonly,
        }

        # Add resource links
        registry_name_for_linking = _get_registry_name_for_linking(registry_mode, registry)
        result = add_links_to_response(result, "registry", registry_name_for_linking)

        return result
    except Exception as e:
        return create_error_response(
            str(e),
            error_code="REGISTRY_CONNECTION_TEST_FAILED",
            registry_mode=registry_mode,
        )


@structured_output("test_all_registries", fallback_on_error=True)
async def test_all_registries_tool(registry_manager, registry_mode: str) -> Dict[str, Any]:
    """
    Test connections to all configured registries with comprehensive metadata and resource links.

    Args:
        registry_manager: The registry manager instance
        registry_mode: Current registry mode (single/multi)

    Returns:
        Dictionary containing test results for all registries with structured validation and navigation links
    """
    try:
        if registry_mode == "single":
            default_registry = registry_manager.get_default_registry()
            if default_registry:
                client = registry_manager.get_registry(default_registry)
                if client:
                    result = client.test_connection()

                    # Add metadata to the test result
                    try:
                        metadata = client.get_server_metadata()
                        result["server_metadata"] = metadata
                    except Exception as e:
                        result["metadata_error"] = str(e)

                    # Add health assessment
                    result["health_assessment"] = {
                        "status": ("healthy" if result.get("status") == "connected" else "unhealthy"),
                        "can_perform_operations": result.get("status") == "connected" and not client.config.readonly,
                        "viewonly_mode": client.config.readonly,
                    }

                    # Convert to enhanced response format
                    response = {
                        "registry_tests": {default_registry: result},
                        "total_registries": 1,
                        "connected": (1 if result.get("status") == "connected" else 0),
                        "failed": 0 if result.get("status") == "connected" else 1,
                        "test_timestamp": __import__("datetime").datetime.now().isoformat(),
                        "registry_mode": "single",
                        "mcp_protocol_version": "2025-06-18",
                    }

                    # Add resource links
                    registry_name_for_linking = _get_registry_name_for_linking(registry_mode, default_registry)
                    response = add_links_to_response(response, "registry", registry_name_for_linking)

                    return response

            return create_error_response(
                "No registry configured",
                error_code="NO_REGISTRY_CONFIGURED",
                registry_mode="single",
            )
        else:
            # Multi-registry mode: use async testing
            result = await registry_manager.test_all_registries_async()

            # Add structured output metadata
            result["registry_mode"] = "multi"
            result["mcp_protocol_version"] = "2025-06-18"
            result["test_timestamp"] = __import__("datetime").datetime.now().isoformat()

            # Add metadata to each registry test result
            if "registry_tests" in result:
                for registry_name, test_result in result["registry_tests"].items():
                    if isinstance(test_result, dict) and "error" not in test_result:
                        try:
                            client = registry_manager.get_registry(registry_name)
                            if client:
                                metadata = client.get_server_metadata()
                                test_result["server_metadata"] = metadata

                                # Add registry configuration info
                                test_result["registry_config"] = {
                                    "name": client.config.name,
                                    "url": client.config.url,
                                    "description": client.config.description,
                                    "viewonly": client.config.readonly,
                                    "has_authentication": bool(client.config.user and client.config.password),
                                }

                                # Add health assessment
                                test_result["health_assessment"] = {
                                    "status": ("healthy" if test_result.get("status") == "connected" else "unhealthy"),
                                    "can_perform_operations": test_result.get("status") == "connected"
                                    and not client.config.readonly,
                                    "viewonly_mode": client.config.readonly,
                                }
                        except Exception as e:
                            test_result["metadata_error"] = str(e)

            # Add summary statistics
            if "registry_tests" in result:
                connected_registries = [
                    name for name, test in result["registry_tests"].items() if test.get("status") == "connected"
                ]
                failed_registries = [
                    name for name, test in result["registry_tests"].items() if test.get("status") != "connected"
                ]

                result["summary"] = {
                    "connected_registries": connected_registries,
                    "failed_registries": failed_registries,
                    "health_status": "healthy" if not failed_registries else "degraded",
                    "success_rate": (
                        f"{(len(connected_registries) / len(result['registry_tests'])) * 100:.1f}%"
                        if result["registry_tests"]
                        else "0%"
                    ),
                    "total_registries": len(result["registry_tests"]),
                    "operational_registries": len(
                        [
                            name
                            for name, test in result["registry_tests"].items()
                            if test.get("status") == "connected"
                            and test.get("health_assessment", {}).get("can_perform_operations", False)
                        ]
                    ),
                }

            # Add resource links - use first connected registry or default
            first_registry = None
            if "registry_tests" in result and result["registry_tests"]:
                # Prefer connected registries
                connected = [
                    name for name, test in result["registry_tests"].items() if test.get("status") == "connected"
                ]
                first_registry = connected[0] if connected else list(result["registry_tests"].keys())[0]

            if first_registry:
                # Add links to the overall test results, pointing to a representative registry
                result["_links"] = {
                    "registries": f"registry://{first_registry}/info",
                    "example_registry": f"registry://{first_registry}",
                }

            return result
    except Exception as e:
        return create_error_response(
            str(e),
            error_code="REGISTRY_CONNECTION_TEST_ALL_FAILED",
            registry_mode=registry_mode,
        )
