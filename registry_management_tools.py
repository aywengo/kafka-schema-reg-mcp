#!/usr/bin/env python3
"""
Registry Management Tools Module - Updated with Structured Output

Handles registry management operations with structured tool output
support per MCP 2025-06-18 specification.

Provides registry listing, connection testing, and information retrieval
with JSON Schema validation and type-safe responses.
"""

from typing import Any, Dict, List, Optional

from schema_validation import (
    create_error_response,
    create_success_response,
    structured_output,
)


@structured_output("list_registries", fallback_on_error=True)
def list_registries_tool(registry_manager, registry_mode: str) -> List[Dict[str, Any]]:
    """
    List all configured Schema Registry instances with structured validation.

    Args:
        registry_manager: The registry manager instance
        registry_mode: Current registry mode (single/multi)

    Returns:
        List of registry information dictionaries with structured validation
    """
    try:
        result = []
        for name in registry_manager.list_registries():
            info = registry_manager.get_registry_info(name)
            if info:
                # Add structured output metadata
                info["registry_mode"] = registry_mode
                info["mcp_protocol_version"] = "2025-06-18"
                result.append(info)

        # If no registries found, return empty list with metadata
        if not result:
            return create_success_response(
                "No registries configured",
                data={"registries": [], "total_count": 0},
                registry_mode=registry_mode,
            )

        # Add summary metadata to first registry for overall information
        if result:
            result[0]["_summary"] = {
                "total_registries": len(result),
                "registry_mode": registry_mode,
                "mcp_protocol_version": "2025-06-18",
            }

        return result
    except Exception as e:
        return create_error_response(
            str(e), error_code="REGISTRY_LIST_FAILED", registry_mode=registry_mode
        )


@structured_output("get_registry_info", fallback_on_error=True)
def get_registry_info_tool(
    registry_manager, registry_mode: str, registry_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific registry with structured validation.

    Args:
        registry_manager: The registry manager instance
        registry_mode: Current registry mode (single/multi)
        registry_name: Optional registry name

    Returns:
        Dictionary containing detailed registry information with structured validation
    """
    try:
        if registry_mode == "single" and not registry_name:
            registry_name = registry_manager.get_default_registry()

        info = registry_manager.get_registry_info(registry_name)
        if info is None:
            return create_error_response(
                f"Registry '{registry_name}' not found",
                error_code="REGISTRY_NOT_FOUND",
                registry_mode=registry_mode,
            )

        # Add structured output metadata
        info["registry_mode"] = registry_mode
        info["mcp_protocol_version"] = "2025-06-18"

        # Add additional metadata for better context
        info["_metadata"] = {
            "queried_registry": registry_name,
            "is_default": registry_name == registry_manager.get_default_registry(),
            "query_timestamp": __import__("datetime").datetime.now().isoformat(),
        }

        return info
    except Exception as e:
        return create_error_response(
            str(e), error_code="REGISTRY_INFO_FAILED", registry_mode=registry_mode
        )


@structured_output("test_registry_connection", fallback_on_error=True)
def test_registry_connection_tool(
    registry_manager, registry_mode: str, registry_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Test connection to a specific registry with comprehensive information including metadata.

    Args:
        registry_manager: The registry manager instance
        registry_mode: Current registry mode (single/multi)
        registry_name: Optional registry name

    Returns:
        Dictionary containing connection test results with structured validation
    """
    try:
        if registry_mode == "single" and not registry_name:
            registry_name = registry_manager.get_default_registry()

        client = registry_manager.get_registry(registry_name)
        if client is None:
            return create_error_response(
                f"Registry '{registry_name}' not found",
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
            "readonly": client.config.readonly,
            "has_authentication": bool(client.config.user and client.config.password),
        }

        return result
    except Exception as e:
        return create_error_response(
            str(e),
            error_code="REGISTRY_CONNECTION_TEST_FAILED",
            registry_mode=registry_mode,
        )


@structured_output("test_all_registries", fallback_on_error=True)
async def test_all_registries_tool(
    registry_manager, registry_mode: str
) -> Dict[str, Any]:
    """
    Test connections to all configured registries with comprehensive metadata.

    Args:
        registry_manager: The registry manager instance
        registry_mode: Current registry mode (single/multi)

    Returns:
        Dictionary containing test results for all registries with structured validation
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

                    return create_success_response(
                        "Single registry connection test completed",
                        data={
                            "registry_tests": {default_registry: result},
                            "total_registries": 1,
                            "connected": (
                                1 if result.get("status") == "connected" else 0
                            ),
                            "failed": 0 if result.get("status") == "connected" else 1,
                            "test_timestamp": __import__("datetime")
                            .datetime.now()
                            .isoformat(),
                        },
                        registry_mode="single",
                    )

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
                                    "readonly": client.config.readonly,
                                    "has_authentication": bool(
                                        client.config.user and client.config.password
                                    ),
                                }
                        except Exception as e:
                            test_result["metadata_error"] = str(e)

            # Add summary statistics
            if "registry_tests" in result:
                connected_registries = [
                    name
                    for name, test in result["registry_tests"].items()
                    if test.get("status") == "connected"
                ]
                failed_registries = [
                    name
                    for name, test in result["registry_tests"].items()
                    if test.get("status") != "connected"
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
                }

            return result
    except Exception as e:
        return create_error_response(
            str(e),
            error_code="REGISTRY_CONNECTION_TEST_ALL_FAILED",
            registry_mode=registry_mode,
        )
