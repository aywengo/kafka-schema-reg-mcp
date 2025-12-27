#!/usr/bin/env python3
"""
Core Registry Tools Module - Updated with Resource Linking

Handles basic CRUD operations for Schema Registry with structured tool output
support per MCP 2025-06-18 specification including resource linking.

Provides schema, subject, configuration, and mode management functionality
with JSON Schema validation, type-safe responses, and HATEOAS navigation links.
"""

import json
import logging
from typing import Any, Dict, Optional

import aiohttp

from resource_linking import add_links_to_response
from schema_registry_common import check_viewonly_mode as _check_viewonly_mode

logger = logging.getLogger(__name__)
from schema_validation import (
    create_error_response,
    create_success_response,
    structured_output,
    validate_registry_response,
)


def build_context_url_legacy(base_url: str, schema_registry_url: str, context: Optional[str] = None) -> str:
    """Build URL with optional context support (legacy function for single-registry mode)."""
    if context and context != ".":
        return f"{schema_registry_url}/contexts/{context}{base_url}"
    return f"{schema_registry_url}{base_url}"


def _get_registry_name(registry_mode: str, registry: Optional[str] = None, client=None) -> str:
    """Helper function to get registry name for linking."""
    if registry_mode == "single":
        return "default"
    elif client and hasattr(client, "config"):
        return client.config.name
    elif registry:
        return registry
    else:
        return "unknown"


# ===== SCHEMA MANAGEMENT TOOLS =====


@structured_output("register_schema", fallback_on_error=True)
def register_schema_tool(
    subject: str,
    schema_definition: Dict[str, Any],
    registry_manager,
    registry_mode: str,
    schema_type: str = "AVRO",
    context: Optional[str] = None,
    registry: Optional[str] = None,
    auth=None,
    headers=None,
    schema_registry_url: str = "",
) -> Dict[str, Any]:
    """
    Register a new schema version under the specified subject.

    Args:
        subject: The subject name for the schema
        schema_definition: The schema definition as a dictionary
        schema_type: The schema type (AVRO, JSON, PROTOBUF)
        context: Optional schema context
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Dictionary containing the schema ID with structured validation and resource links
    """
    # Check viewonly mode
    viewonly_check = _check_viewonly_mode(registry_manager, registry)
    if viewonly_check:
        return validate_registry_response(viewonly_check, registry_mode)

    try:
        if registry_mode == "single":
            # Single-registry mode: use secure session approach
            client = registry_manager.get_registry()
            if client is None:
                return create_error_response(
                    "No default registry configured",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="single",
                )

            payload = {
                "schema": json.dumps(schema_definition),
                "schemaType": schema_type,
            }

            url = client.build_context_url(f"/subjects/{subject}/versions", context)

            response = client.session.post(url, data=json.dumps(payload), auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Add structured output metadata
            result["subject"] = subject
            result["registry_mode"] = "single"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            registry_name = _get_registry_name(registry_mode, registry)
            if "id" in result:
                # Use the returned version or assume latest
                version = result.get("version", "latest")
                result = add_links_to_response(
                    result,
                    "schema",
                    registry_name,
                    subject=subject,
                    version=version,
                    context=context,
                )

            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            payload = {
                "schema": json.dumps(schema_definition),
                "schemaType": schema_type,
            }

            url = client.build_context_url(f"/subjects/{subject}/versions", context)

            response = client.session.post(url, data=json.dumps(payload), auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Add structured output metadata
            result["subject"] = subject
            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            if "id" in result:
                # Use the returned version or assume latest
                version = result.get("version", "latest")
                result = add_links_to_response(
                    result,
                    "schema",
                    client.config.name,
                    subject=subject,
                    version=version,
                    context=context,
                )

            return result
    except Exception as e:
        return create_error_response(str(e), error_code="REGISTRATION_FAILED", registry_mode=registry_mode)


@structured_output("get_schema", fallback_on_error=True)
def get_schema_tool(
    subject: str,
    registry_manager,
    registry_mode: str,
    version: str = "latest",
    context: Optional[str] = None,
    registry: Optional[str] = None,
    auth=None,
    headers=None,
    schema_registry_url: str = "",
) -> Dict[str, Any]:
    """
    Get a specific version of a schema.

    Args:
        subject: The subject name
        version: The schema version (default: latest)
        context: Optional schema context
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Dictionary containing schema information with structured validation and resource links
    """
    try:
        if registry_mode == "single":
            # Single-registry mode: use secure session approach
            client = registry_manager.get_registry()
            if client is None:
                return create_error_response(
                    "No default registry configured",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="single",
                )

            url = client.build_context_url(f"/subjects/{subject}/versions/{version}", context)

            response = client.session.get(url, auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Ensure schema is parsed as JSON object if it's a string
            if isinstance(result.get("schema"), str):
                try:
                    result["schema"] = json.loads(result["schema"])
                except (json.JSONDecodeError, TypeError):
                    # Keep as string if not valid JSON
                    pass

            # Add structured output metadata
            result["registry_mode"] = "single"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            registry_name = _get_registry_name(registry_mode, registry)
            result = add_links_to_response(
                result,
                "schema",
                registry_name,
                subject=subject,
                version=version,
                context=context,
            )

            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            url = client.build_context_url(f"/subjects/{subject}/versions/{version}", context)

            response = client.session.get(url, auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Ensure schema is parsed as JSON object if it's a string
            if isinstance(result.get("schema"), str):
                try:
                    result["schema"] = json.loads(result["schema"])
                except (json.JSONDecodeError, TypeError):
                    # Keep as string if not valid JSON
                    pass

            # Add structured output metadata
            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            result = add_links_to_response(
                result,
                "schema",
                client.config.name,
                subject=subject,
                version=version,
                context=context,
            )

            return result
    except Exception as e:
        return create_error_response(str(e), error_code="SCHEMA_RETRIEVAL_FAILED", registry_mode=registry_mode)


@structured_output("get_schema_versions", fallback_on_error=True)
def get_schema_versions_tool(
    subject: str,
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None,
    auth=None,
    headers=None,
    schema_registry_url: str = "",
) -> Dict[str, Any]:
    """
    Get all versions of a schema for a subject.

    Args:
        subject: The subject name
        context: Optional schema context
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Dictionary containing version numbers with structured validation and resource links
    """
    try:
        if registry_mode == "single":
            # Single-registry mode: use secure session approach
            client = registry_manager.get_registry()
            if client is None:
                return create_error_response(
                    "No default registry configured",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="single",
                )

            url = client.build_context_url(f"/subjects/{subject}/versions", context)

            response = client.session.get(url, auth=client.auth, headers=client.headers)

            # Handle 404 specifically - subject doesn't exist
            if response.status_code == 404:
                versions_list = []
            else:
                response.raise_for_status()
                versions_list = response.json()

            # Convert to enhanced response format
            result = {
                "subject": subject,
                "versions": versions_list,
                "registry_mode": "single",
                "mcp_protocol_version": "2025-11-25",
            }

            # Add resource links
            registry_name = _get_registry_name(registry_mode, registry)
            result = add_links_to_response(
                result,
                "schema_versions",
                registry_name,
                subject=subject,
                context=context,
            )

            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            url = client.build_context_url(f"/subjects/{subject}/versions", context)

            response = client.session.get(url, auth=client.auth, headers=client.headers)

            # Handle 404 specifically - subject doesn't exist
            if response.status_code == 404:
                versions_list = []
            else:
                response.raise_for_status()
                versions_list = response.json()

            # Convert to enhanced response format
            result = {
                "subject": subject,
                "versions": versions_list,
                "registry": client.config.name,
                "registry_mode": "multi",
                "mcp_protocol_version": "2025-11-25",
            }

            # Add resource links
            result = add_links_to_response(
                result,
                "schema_versions",
                client.config.name,
                subject=subject,
                context=context,
            )

            return result
    except Exception as e:
        return create_error_response(str(e), error_code="VERSION_RETRIEVAL_FAILED", registry_mode=registry_mode)


@structured_output("list_subjects", fallback_on_error=True)
def list_subjects_tool(
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None,
    auth=None,
    headers=None,
    schema_registry_url: str = "",
) -> Dict[str, Any]:
    """
    List all subjects, optionally filtered by context.

    Args:
        context: Optional schema context to filter by
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Dictionary containing subject names with structured validation and resource links
    """
    try:
        if registry_mode == "single":
            # Single-registry mode: use secure session approach
            client = registry_manager.get_registry()
            if client is None:
                return create_error_response(
                    "No default registry configured",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="single",
                )

            url = client.build_context_url("/subjects", context)

            response = client.session.get(url, auth=client.auth, headers=client.headers)
            response.raise_for_status()
            subjects_list = response.json()

            # Convert to enhanced response format
            result = {
                "subjects": subjects_list,
                "context": context,
                "registry_mode": "single",
                "mcp_protocol_version": "2025-11-25",
            }

            # Add resource links
            registry_name = _get_registry_name(registry_mode, registry)
            result = add_links_to_response(result, "subjects_list", registry_name, context=context)

            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            subjects_list = client.get_subjects(context)

            # Convert to enhanced response format
            result = {
                "subjects": subjects_list,
                "context": context,
                "registry": client.config.name,
                "registry_mode": "multi",
                "mcp_protocol_version": "2025-11-25",
            }

            # Add resource links
            result = add_links_to_response(result, "subjects_list", client.config.name, context=context)

            return result
    except Exception as e:
        return create_error_response(str(e), error_code="SUBJECT_LIST_FAILED", registry_mode=registry_mode)


@structured_output("check_compatibility", fallback_on_error=True)
def check_compatibility_tool(
    subject: str,
    schema_definition: Dict[str, Any],
    registry_manager,
    registry_mode: str,
    schema_type: str = "AVRO",
    context: Optional[str] = None,
    registry: Optional[str] = None,
    auth=None,
    headers=None,
    schema_registry_url: str = "",
) -> Dict[str, Any]:
    """
    Check if a schema is compatible with the latest version.

    Args:
        subject: The subject name
        schema_definition: The schema definition to check
        schema_type: The schema type (AVRO, JSON, PROTOBUF)
        context: Optional schema context
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Compatibility check result with structured validation and resource links
    """
    try:
        payload = {"schema": json.dumps(schema_definition), "schemaType": schema_type}

        if registry_mode == "single":
            # Single-registry mode: use secure session approach
            client = registry_manager.get_registry()
            if client is None:
                return create_error_response(
                    "No default registry configured",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="single",
                )

            url = client.build_context_url(f"/compatibility/subjects/{subject}/versions/latest", context)

            response = client.session.post(url, data=json.dumps(payload), auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Add structured output metadata and normalize field names
            if "is_compatible" not in result:
                if "isCompatible" in result:
                    result["is_compatible"] = result.pop("isCompatible")
                elif "compatible" in result:
                    result["is_compatible"] = result.pop("compatible")
                else:
                    # Fallback: set default value if no compatibility field is found
                    logger.warning(f"No compatibility field found in response: {result.keys()}")
                    result["is_compatible"] = False

            result["registry_mode"] = "single"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            registry_name = _get_registry_name(registry_mode, registry)
            result = add_links_to_response(result, "compatibility", registry_name, subject=subject, context=context)

            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            url = client.build_context_url(f"/compatibility/subjects/{subject}/versions/latest", context)

            response = client.session.post(url, data=json.dumps(payload), auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Add structured output metadata and normalize field names
            if "is_compatible" not in result:
                if "isCompatible" in result:
                    result["is_compatible"] = result.pop("isCompatible")
                elif "compatible" in result:
                    result["is_compatible"] = result.pop("compatible")
                else:
                    # Fallback: set default value if no compatibility field is found
                    logger.warning(f"No compatibility field found in response: {result.keys()}")
                    result["is_compatible"] = False

            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            result = add_links_to_response(
                result,
                "compatibility",
                client.config.name,
                subject=subject,
                context=context,
            )

            return result
    except Exception as e:
        return create_error_response(str(e), error_code="COMPATIBILITY_CHECK_FAILED", registry_mode=registry_mode)


# ===== CONFIGURATION MANAGEMENT TOOLS =====


@structured_output("get_global_config", fallback_on_error=True)
def get_global_config_tool(
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None,
    auth=None,
    standard_headers=None,
    schema_registry_url: str = "",
) -> Dict[str, Any]:
    """
    Get global configuration settings.

    Args:
        context: Optional schema context
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Dictionary containing configuration with structured validation and resource links
    """
    try:
        if registry_mode == "single":
            # Single-registry mode: use secure session approach
            client = registry_manager.get_registry()
            if client is None:
                return create_error_response(
                    "No default registry configured",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="single",
                )

            url = client.build_context_url("/config", context)

            response = client.session.get(url, auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Map Schema Registry API response to expected schema format
            if "compatibilityLevel" in result:
                result["compatibility"] = result.pop("compatibilityLevel")

            # Add structured output metadata
            result["registry_mode"] = "single"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            registry_name = _get_registry_name(registry_mode, registry)
            result = add_links_to_response(result, "config", registry_name, context=context)

            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            url = client.build_context_url("/config", context)

            response = client.session.get(url, auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Map Schema Registry API response to expected schema format
            if "compatibilityLevel" in result:
                result["compatibility"] = result.pop("compatibilityLevel")

            # Add structured output metadata
            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            result = add_links_to_response(result, "config", client.config.name, context=context)

            return result
    except Exception as e:
        return create_error_response(str(e), error_code="CONFIG_RETRIEVAL_FAILED", registry_mode=registry_mode)


@structured_output("update_global_config", fallback_on_error=True)
def update_global_config_tool(
    compatibility: str,
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None,
    auth=None,
    standard_headers=None,
    schema_registry_url: str = "",
) -> Dict[str, Any]:
    """
    Update global configuration settings.

    Args:
        compatibility: Compatibility level (BACKWARD, FORWARD, FULL, NONE, etc.)
        context: Optional schema context
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Updated configuration with structured validation and resource links
    """
    # Check viewonly mode
    viewonly_check = _check_viewonly_mode(registry_manager, registry)
    if viewonly_check:
        return validate_registry_response(viewonly_check, registry_mode)

    try:
        payload = {"compatibility": compatibility}

        if registry_mode == "single":
            # Single-registry mode: use secure session approach
            client = registry_manager.get_registry()
            if client is None:
                return create_error_response(
                    "No default registry configured",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="single",
                )

            url = client.build_context_url("/config", context)

            response = client.session.put(url, data=json.dumps(payload), auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Ensure the compatibility field is present in the response (required by schema validation)
            if "compatibility" not in result:
                result["compatibility"] = compatibility

            # Add structured output metadata
            result["registry_mode"] = "single"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            registry_name = _get_registry_name(registry_mode, registry)
            result = add_links_to_response(result, "config", registry_name, context=context)

            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            url = client.build_context_url("/config", context)

            response = client.session.put(url, data=json.dumps(payload), auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Ensure the compatibility field is present in the response (required by schema validation)
            if "compatibility" not in result:
                result["compatibility"] = compatibility

            # Add structured output metadata
            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            result = add_links_to_response(result, "config", client.config.name, context=context)

            return result
    except Exception as e:
        return create_error_response(str(e), error_code="CONFIG_UPDATE_FAILED", registry_mode=registry_mode)


@structured_output("get_subject_config", fallback_on_error=True)
def get_subject_config_tool(
    subject: str,
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None,
    auth=None,
    standard_headers=None,
    schema_registry_url: str = "",
) -> Dict[str, Any]:
    """
    Get configuration settings for a specific subject.

    Args:
        subject: The subject name
        context: Optional schema context
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Dictionary containing subject configuration with structured validation and resource links
    """
    try:
        if registry_mode == "single":
            # Single-registry mode: use secure session approach
            client = registry_manager.get_registry()
            if client is None:
                return create_error_response(
                    "No default registry configured",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="single",
                )

            url = client.build_context_url(f"/config/{subject}", context)

            response = client.session.get(url, auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Map Schema Registry API response to expected schema format
            if "compatibilityLevel" in result:
                result["compatibility"] = result.pop("compatibilityLevel")

            # Add structured output metadata
            result["registry_mode"] = "single"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            registry_name = _get_registry_name(registry_mode, registry)
            result = add_links_to_response(result, "config", registry_name, subject=subject, context=context)

            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            url = client.build_context_url(f"/config/{subject}", context)

            response = client.session.get(url, auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Map Schema Registry API response to expected schema format
            if "compatibilityLevel" in result:
                result["compatibility"] = result.pop("compatibilityLevel")

            # Add structured output metadata
            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            result = add_links_to_response(result, "config", client.config.name, subject=subject, context=context)

            return result
    except Exception as e:
        return create_error_response(
            str(e),
            error_code="SUBJECT_CONFIG_RETRIEVAL_FAILED",
            registry_mode=registry_mode,
        )


@structured_output("update_subject_config", fallback_on_error=True)
def update_subject_config_tool(
    subject: str,
    compatibility: str,
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None,
    auth=None,
    standard_headers=None,
    schema_registry_url: str = "",
) -> Dict[str, Any]:
    """
    Update configuration settings for a specific subject.

    Args:
        subject: The subject name
        compatibility: Compatibility level (BACKWARD, FORWARD, FULL, NONE, etc.)
        context: Optional schema context
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Updated configuration with structured validation and resource links
    """
    # Check viewonly mode
    viewonly_check = _check_viewonly_mode(registry_manager, registry)
    if viewonly_check:
        return validate_registry_response(viewonly_check, registry_mode)

    try:
        payload = {"compatibility": compatibility}

        if registry_mode == "single":
            # Single-registry mode: use secure session approach
            client = registry_manager.get_registry()
            if client is None:
                return create_error_response(
                    "No default registry configured",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="single",
                )

            url = client.build_context_url(f"/config/{subject}", context)
            response = client.session.put(url, data=json.dumps(payload), auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Ensure the compatibility field is present in the response (required by schema validation)
            if "compatibility" not in result:
                result["compatibility"] = compatibility

            # Add structured output metadata
            result["registry_mode"] = "single"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            registry_name = _get_registry_name(registry_mode, registry)
            result = add_links_to_response(result, "config", registry_name, subject=subject, context=context)

            return result
        else:
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            url = client.build_context_url(f"/config/{subject}", context)
            response = client.session.put(url, data=json.dumps(payload), auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Ensure the compatibility field is present in the response (required by schema validation)
            if "compatibility" not in result:
                result["compatibility"] = compatibility

            # Add structured output metadata
            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            result = add_links_to_response(result, "config", client.config.name, subject=subject, context=context)

            return result
    except Exception as e:
        return create_error_response(
            str(e),
            error_code="SUBJECT_CONFIG_UPDATE_FAILED",
            registry_mode=registry_mode,
        )


@structured_output("add_subject_alias", fallback_on_error=True)
def add_subject_alias_tool(
    alias: str,
    existing_subject: str,
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None,
    auth=None,
    standard_headers=None,
    schema_registry_url: str = "",
) -> Dict[str, Any]:
    """
    Create a subject alias that points to an existing subject.

    Args:
        alias: The new subject alias to create
        existing_subject: The existing subject to alias to
        context: Optional schema context
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Result from registry with structured validation and resource links
    """
    # Block in VIEWONLY mode
    viewonly_check = _check_viewonly_mode(registry_manager, registry)
    if viewonly_check:
        return validate_registry_response(viewonly_check, registry_mode)

    try:
        payload = {"alias": existing_subject}

        if registry_mode == "single":
            client = registry_manager.get_registry()
            if client is None:
                return create_error_response(
                    "No default registry configured",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="single",
                )

            url = client.build_context_url(f"/config/{alias}", context)
            response = client.session.put(
                url, data=json.dumps(payload), auth=client.auth, headers=client.standard_headers
            )
            response.raise_for_status()
            result = (
                response.json()
                if response.headers.get("Content-Type", "").startswith("application/json")
                else {"status": "ok"}
            )

            # Add metadata and links
            result.setdefault("alias", alias)
            result.setdefault("target", existing_subject)
            result["registry_mode"] = "single"
            result["mcp_protocol_version"] = "2025-11-25"

            registry_name = _get_registry_name(registry_mode, registry)
            result = add_links_to_response(
                result,
                "config",
                registry_name,
                subject=alias,
                context=context,
            )
            return result
        else:
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            url = client.build_context_url(f"/config/{alias}", context)
            response = client.session.put(
                url, data=json.dumps(payload), auth=client.auth, headers=client.standard_headers
            )
            response.raise_for_status()
            result = (
                response.json()
                if response.headers.get("Content-Type", "").startswith("application/json")
                else {"status": "ok"}
            )

            # Add metadata and links
            result.setdefault("alias", alias)
            result.setdefault("target", existing_subject)
            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            result["mcp_protocol_version"] = "2025-11-25"

            result = add_links_to_response(
                result,
                "config",
                client.config.name,
                subject=alias,
                context=context,
            )
            return result
    except Exception as e:
        return create_error_response(str(e), error_code="SUBJECT_ALIAS_FAILED", registry_mode=registry_mode)


@structured_output("delete_subject_alias", fallback_on_error=True)
def delete_subject_alias_tool(
    alias: str,
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None,
    auth=None,
    standard_headers=None,
    schema_registry_url: str = "",
) -> Dict[str, Any]:
    """
    Delete a subject alias.

    Args:
        alias: The alias subject to delete
        context: Optional schema context
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Result with structured validation and resource links
    """
    # Block in VIEWONLY mode
    viewonly_check = _check_viewonly_mode(registry_manager, registry)
    if viewonly_check:
        return validate_registry_response(viewonly_check, registry_mode)

    try:
        if registry_mode == "single":
            client = registry_manager.get_registry()
            if client is None:
                return create_error_response(
                    "No default registry configured",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="single",
                )

            url = client.build_context_url(f"/config/{alias}", context)
            response = client.session.delete(url, auth=client.auth, headers=client.standard_headers)

            # Some registries may return 200/204/404 depending on alias behavior
            if response.status_code not in (200, 204, 404):
                response.raise_for_status()

            result: Dict[str, Any] = {
                "alias": alias,
                "deleted": response.status_code in (200, 204),
                "registry_mode": "single",
                "mcp_protocol_version": "2025-11-25",
            }

            registry_name = _get_registry_name(registry_mode, registry)
            # Link to subjects list/config root
            result = add_links_to_response(result, "config", registry_name, subject=alias, context=context)
            return result
        else:
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            url = client.build_context_url(f"/config/{alias}", context)
            response = client.session.delete(url, auth=client.auth, headers=client.standard_headers)

            if response.status_code not in (200, 204, 404):
                response.raise_for_status()

            result = {
                "alias": alias,
                "deleted": response.status_code in (200, 204),
                "registry": client.config.name,
                "registry_mode": "multi",
                "mcp_protocol_version": "2025-11-25",
            }

            result = add_links_to_response(result, "config", client.config.name, subject=alias, context=context)
            return result
    except Exception as e:
        return create_error_response(str(e), error_code="SUBJECT_ALIAS_DELETE_FAILED", registry_mode=registry_mode)


# ===== MODE MANAGEMENT TOOLS =====


@structured_output("get_mode", fallback_on_error=True)
def get_mode_tool(
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None,
    auth=None,
    standard_headers=None,
    schema_registry_url: str = "",
) -> Dict[str, str]:
    """
    Get the current mode of the Schema Registry.

    Args:
        context: Optional schema context
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Dictionary containing the current mode with structured validation and resource links
    """
    try:
        if registry_mode == "single":
            # Single-registry mode: use secure session approach
            client = registry_manager.get_registry()
            if client is None:
                return create_error_response(
                    "No default registry configured",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="single",
                )

            url = client.build_context_url("/mode", context)

            response = client.session.get(url, auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Add structured output metadata
            result["registry_mode"] = "single"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            registry_name = _get_registry_name(registry_mode, registry)
            result = add_links_to_response(result, "mode", registry_name, context=context)

            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            url = client.build_context_url("/mode", context)

            response = client.session.get(url, auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Add structured output metadata
            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            result = add_links_to_response(result, "mode", client.config.name, context=context)

            return result
    except Exception as e:
        return create_error_response(str(e), error_code="MODE_RETRIEVAL_FAILED", registry_mode=registry_mode)


@structured_output("update_mode", fallback_on_error=True)
def update_mode_tool(
    mode: str,
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None,
    auth=None,
    standard_headers=None,
    schema_registry_url: str = "",
) -> Dict[str, str]:
    """
    Update the mode of the Schema Registry.

    Args:
        mode: The mode to set (IMPORT, READONLY, READWRITE)
        context: Optional schema context
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Updated mode information with structured validation and resource links
    """
    # Check viewonly mode
    viewonly_check = _check_viewonly_mode(registry_manager, registry)
    if viewonly_check:
        return validate_registry_response(viewonly_check, registry_mode)

    try:
        payload = {"mode": mode}

        if registry_mode == "single":
            # Single-registry mode: use secure session approach
            client = registry_manager.get_registry()
            if client is None:
                return create_error_response(
                    "No default registry configured",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="single",
                )

            url = client.build_context_url("/mode", context)

            response = client.session.put(url, data=json.dumps(payload), auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Ensure the mode field is present in the response (required by schema validation)
            if "mode" not in result:
                result["mode"] = mode

            # Add structured output metadata
            result["registry_mode"] = "single"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            registry_name = _get_registry_name(registry_mode, registry)
            result = add_links_to_response(result, "mode", registry_name, context=context)

            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            url = client.build_context_url("/mode", context)

            response = client.session.put(url, data=json.dumps(payload), auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Ensure the mode field is present in the response (required by schema validation)
            if "mode" not in result:
                result["mode"] = mode

            # Add structured output metadata
            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            result = add_links_to_response(result, "mode", client.config.name, context=context)

            return result
    except Exception as e:
        return create_error_response(str(e), error_code="MODE_UPDATE_FAILED", registry_mode=registry_mode)


@structured_output("get_subject_mode", fallback_on_error=True)
def get_subject_mode_tool(
    subject: str,
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None,
    auth=None,
    standard_headers=None,
    schema_registry_url: str = "",
) -> Dict[str, str]:
    """
    Get the mode for a specific subject.

    Args:
        subject: The subject name
        context: Optional schema context
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Dictionary containing the subject mode with structured validation and resource links
    """
    try:
        if registry_mode == "single":
            # Single-registry mode: use secure session approach
            client = registry_manager.get_registry()
            if client is None:
                return create_error_response(
                    "No default registry configured",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="single",
                )

            url = client.build_context_url(f"/mode/{subject}", context)

            response = client.session.get(url, auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Add structured output metadata
            result["registry_mode"] = "single"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            registry_name = _get_registry_name(registry_mode, registry)
            result = add_links_to_response(result, "mode", registry_name, subject=subject, context=context)

            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            url = client.build_context_url(f"/mode/{subject}", context)

            response = client.session.get(url, auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Add structured output metadata
            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            result = add_links_to_response(result, "mode", client.config.name, subject=subject, context=context)

            return result
    except Exception as e:
        return create_error_response(
            str(e),
            error_code="SUBJECT_MODE_RETRIEVAL_FAILED",
            registry_mode=registry_mode,
        )


@structured_output("update_subject_mode", fallback_on_error=True)
def update_subject_mode_tool(
    subject: str,
    mode: str,
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None,
    auth=None,
    standard_headers=None,
    schema_registry_url: str = "",
) -> Dict[str, str]:
    """
    Update the mode for a specific subject.

    Args:
        subject: The subject name
        mode: The mode to set (IMPORT, READONLY, READWRITE)
        context: Optional schema context
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Updated mode information with structured validation and resource links
    """
    # Check viewonly mode
    viewonly_check = _check_viewonly_mode(registry_manager, registry)
    if viewonly_check:
        return validate_registry_response(viewonly_check, registry_mode)

    try:
        payload = {"mode": mode}

        if registry_mode == "single":
            # Single-registry mode: use secure session approach
            client = registry_manager.get_registry()
            if client is None:
                return create_error_response(
                    "No default registry configured",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="single",
                )

            url = client.build_context_url(f"/mode/{subject}", context)

            response = client.session.put(url, data=json.dumps(payload), auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Ensure the mode field is present in the response (required by schema validation)
            if "mode" not in result:
                result["mode"] = mode

            # Add structured output metadata
            result["registry_mode"] = "single"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            registry_name = _get_registry_name(registry_mode, registry)
            result = add_links_to_response(result, "mode", registry_name, subject=subject, context=context)

            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            url = client.build_context_url(f"/mode/{subject}", context)

            response = client.session.put(url, data=json.dumps(payload), auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Ensure the mode field is present in the response (required by schema validation)
            if "mode" not in result:
                result["mode"] = mode

            # Add structured output metadata
            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            result = add_links_to_response(result, "mode", client.config.name, subject=subject, context=context)

            return result
    except Exception as e:
        return create_error_response(str(e), error_code="SUBJECT_MODE_UPDATE_FAILED", registry_mode=registry_mode)


# ===== CONTEXT AND SUBJECT MANAGEMENT =====


@structured_output("list_contexts", fallback_on_error=True)
def list_contexts_tool(
    registry_manager,
    registry_mode: str,
    registry: Optional[str] = None,
    auth=None,
    headers=None,
    schema_registry_url: str = "",
) -> Dict[str, Any]:
    """
    List all available schema contexts.

    Args:
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Dictionary containing context names with structured validation and resource links
    """
    try:
        if registry_mode == "single":
            # Single-registry mode: use secure session approach
            client = registry_manager.get_registry()
            if client is None:
                return create_error_response(
                    "No default registry configured",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="single",
                )

            response = client.session.get(f"{client.config.url}/contexts", auth=client.auth, headers=client.headers)
            response.raise_for_status()
            contexts_list = response.json()

            # Convert to enhanced response format
            result = {
                "contexts": contexts_list,
                "registry_mode": "single",
                "mcp_protocol_version": "2025-11-25",
            }

            # Add resource links
            registry_name = _get_registry_name(registry_mode, registry)
            result = add_links_to_response(result, "contexts_list", registry_name)

            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            contexts_list = client.get_contexts()

            # Convert to enhanced response format
            result = {
                "contexts": contexts_list,
                "registry": client.config.name,
                "registry_mode": "multi",
                "mcp_protocol_version": "2025-11-25",
            }

            # Add resource links
            result = add_links_to_response(result, "contexts_list", client.config.name)

            return result
    except Exception as e:
        return create_error_response(str(e), error_code="CONTEXT_LIST_FAILED", registry_mode=registry_mode)


@structured_output("create_context", fallback_on_error=True)
def create_context_tool(
    context: str,
    registry_manager,
    registry_mode: str,
    registry: Optional[str] = None,
    auth=None,
    headers=None,
    schema_registry_url: str = "",
) -> Dict[str, str]:
    """
    Create a new schema context.

    Args:
        context: The context name to create
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Success message with structured validation and resource links
    """
    # Check viewonly mode
    viewonly_check = _check_viewonly_mode(registry_manager, registry)
    if viewonly_check:
        return validate_registry_response(viewonly_check, registry_mode)

    try:
        if registry_mode == "single":
            # Single-registry mode: use secure session approach
            client = registry_manager.get_registry()
            if client is None:
                return create_error_response(
                    "No default registry configured",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="single",
                )

            response = client.session.post(
                f"{client.config.url}/contexts/{context}", auth=client.auth, headers=client.headers
            )
            response.raise_for_status()
            result = create_success_response(f"Context '{context}' created successfully", registry_mode="single")

            # Add resource links
            registry_name = _get_registry_name(registry_mode, registry)
            result = add_links_to_response(result, "context", registry_name, context=context)

            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            response = client.session.post(
                f"{client.config.url}/contexts/{context}", auth=client.auth, headers=client.headers
            )
            response.raise_for_status()
            result = create_success_response(
                f"Context '{context}' created successfully",
                data={"registry": client.config.name},
                registry_mode="multi",
            )

            # Add resource links
            result = add_links_to_response(result, "context", client.config.name, context=context)

            return result
    except Exception as e:
        return create_error_response(str(e), error_code="CONTEXT_CREATE_FAILED", registry_mode=registry_mode)


@structured_output("delete_context", fallback_on_error=True)
def delete_context_tool(
    context: str,
    registry_manager,
    registry_mode: str,
    registry: Optional[str] = None,
    auth=None,
    headers=None,
    schema_registry_url: str = "",
) -> Dict[str, str]:
    """
    Delete a schema context.

    Args:
        context: The context name to delete
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Success message with structured validation and resource links
    """
    # Check viewonly mode
    viewonly_check = _check_viewonly_mode(registry_manager, registry)
    if viewonly_check:
        return validate_registry_response(viewonly_check, registry_mode)

    try:
        if registry_mode == "single":
            # Single-registry mode: use secure session approach
            client = registry_manager.get_registry()
            if client is None:
                return create_error_response(
                    "No default registry configured",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="single",
                )

            response = client.session.delete(
                f"{client.config.url}/contexts/{context}", auth=client.auth, headers=client.headers
            )
            response.raise_for_status()
            result = create_success_response(f"Context '{context}' deleted successfully", registry_mode="single")

            # Add links to contexts list since the specific context is now deleted
            registry_name = _get_registry_name(registry_mode, registry)
            result = add_links_to_response(result, "contexts_list", registry_name)

            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            response = client.session.delete(
                f"{client.config.url}/contexts/{context}", auth=client.auth, headers=client.headers
            )
            response.raise_for_status()
            result = create_success_response(
                f"Context '{context}' deleted successfully",
                data={"registry": client.config.name},
                registry_mode="multi",
            )

            # Add links to contexts list since the specific context is now deleted
            result = add_links_to_response(result, "contexts_list", client.config.name)

            return result
    except Exception as e:
        return create_error_response(str(e), error_code="CONTEXT_DELETE_FAILED", registry_mode=registry_mode)


@structured_output("delete_subject", fallback_on_error=True)
async def delete_subject_tool(
    subject: str,
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None,
    permanent: bool = False,
    auth=None,
    headers=None,
    schema_registry_url: str = "",
) -> Dict[str, Any]:
    """
    Delete a subject and all its versions.

    Args:
        subject: The subject name to delete
        context: Optional schema context
        registry: Optional registry name (ignored in single-registry mode)
        permanent: If True, perform a hard delete (removes all metadata including schema ID)

    Returns:
        Dictionary containing deleted version numbers with structured validation and resource links
    """
    # Check viewonly mode
    viewonly_check = _check_viewonly_mode(registry_manager, registry)
    if viewonly_check:
        return validate_registry_response(viewonly_check, registry_mode)

    try:
        if registry_mode == "single":
            # Single-registry mode: use secure session approach
            client = registry_manager.get_registry()
            if client is None:
                return create_error_response(
                    "No default registry configured",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="single",
                )

            url = client.build_context_url(f"/subjects/{subject}", context)

            # Add permanent parameter if specified
            if permanent:
                url += "?permanent=true"

            response = client.session.delete(url, auth=client.auth, headers=client.headers)
            response.raise_for_status()
            deleted_versions = response.json()

            # Convert to enhanced response format
            result = {
                "subject": subject,
                "deleted_versions": deleted_versions,
                "permanent": permanent,
                "context": context,
                "registry_mode": "single",
                "mcp_protocol_version": "2025-11-25",
            }

            # Add links to subjects list since the specific subject is now deleted
            registry_name = _get_registry_name(registry_mode, registry)
            result = add_links_to_response(result, "subjects_list", registry_name, context=context)

            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            url = client.build_context_url(f"/subjects/{subject}", context)

            # Add permanent parameter if specified
            if permanent:
                url += "?permanent=true"

            # Use aiohttp for async HTTP requests
            async with aiohttp.ClientSession() as session:
                async with session.delete(url, headers=client.headers) as response:
                    response.raise_for_status()
                    deleted_versions = await response.json()

            # Convert to enhanced response format
            result = {
                "subject": subject,
                "deleted_versions": deleted_versions,
                "permanent": permanent,
                "context": context,
                "registry": client.config.name,
                "registry_mode": "multi",
                "mcp_protocol_version": "2025-11-25",
            }

            # Add links to subjects list since the specific subject is now deleted
            result = add_links_to_response(result, "subjects_list", client.config.name, context=context)

            return result
    except Exception as e:
        return create_error_response(str(e), error_code="SUBJECT_DELETE_FAILED", registry_mode=registry_mode)


@structured_output("get_schema_by_id", fallback_on_error=True)
def get_schema_by_id_tool(
    schema_id: int,
    registry_manager,
    registry_mode: str,
    registry: Optional[str] = None,
    auth=None,
    headers=None,
    schema_registry_url: str = "",
) -> Dict[str, Any]:
    """
    Get a schema by its globally unique ID.

    Args:
        schema_id: The globally unique schema ID
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Dictionary containing schema information with structured validation and resource links
    """
    try:
        if registry_mode == "single":
            # Single-registry mode: use secure session approach
            client = registry_manager.get_registry()
            if client is None:
                return create_error_response(
                    "No default registry configured",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="single",
                )

            # Use the Schema Registry API endpoint for getting schema by ID
            url = f"{client.config.url}/schemas/ids/{schema_id}"

            response = client.session.get(url, auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Parse the schema string if it's returned as a string
            if isinstance(result.get("schema"), str):
                try:
                    result["schema"] = json.loads(result["schema"])
                except (json.JSONDecodeError, TypeError):
                    # Keep as string if not valid JSON
                    pass

            # Add schema ID to the result
            result["id"] = schema_id
            result["registry_mode"] = "single"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            registry_name = _get_registry_name(registry_mode, registry)
            result = add_links_to_response(
                result,
                "schema_by_id",
                registry_name,
                schema_id=schema_id,
            )

            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            # Use the Schema Registry API endpoint for getting schema by ID
            url = f"{client.config.url}/schemas/ids/{schema_id}"

            response = client.session.get(url, auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()

            # Parse the schema string if it's returned as a string
            if isinstance(result.get("schema"), str):
                try:
                    result["schema"] = json.loads(result["schema"])
                except (json.JSONDecodeError, TypeError):
                    # Keep as string if not valid JSON
                    pass

            # Add schema ID to the result
            result["id"] = schema_id
            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            result["mcp_protocol_version"] = "2025-11-25"

            # Add resource links
            result = add_links_to_response(
                result,
                "schema_by_id",
                client.config.name,
                schema_id=schema_id,
            )

            return result
    except Exception as e:
        return create_error_response(str(e), error_code="SCHEMA_ID_LOOKUP_FAILED", registry_mode=registry_mode)


@structured_output("get_subjects_by_schema_id", fallback_on_error=True)
def get_subjects_by_schema_id_tool(
    schema_id: int,
    registry_manager,
    registry_mode: str,
    registry: Optional[str] = None,
    auth=None,
    headers=None,
    schema_registry_url: str = "",
) -> Dict[str, Any]:
    """
    Get subjects associated with a schema ID.

    Args:
        schema_id: The globally unique schema ID
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Dictionary containing list of subjects and versions associated with the schema ID
    """
    try:
        if registry_mode == "single":
            # Single-registry mode: use secure session approach
            client = registry_manager.get_registry()
            if client is None:
                return create_error_response(
                    "No default registry configured",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="single",
                )

            # Use the Schema Registry API endpoint for getting subject-versions by ID
            url = f"{client.config.url}/schemas/ids/{schema_id}/versions"

            response = client.session.get(url, auth=client.auth, headers=client.headers)
            response.raise_for_status()
            subject_versions = response.json()

            result = {
                "schema_id": schema_id,
                "subject_versions": subject_versions,
                "registry_mode": "single",
                "mcp_protocol_version": "2025-11-25",
            }

            # Add resource links
            registry_name = _get_registry_name(registry_mode, registry)
            result = add_links_to_response(
                result,
                "schema_subjects",
                registry_name,
                schema_id=schema_id,
            )

            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode="multi",
                )

            # Use the Schema Registry API endpoint for getting subject-versions by ID
            url = f"{client.config.url}/schemas/ids/{schema_id}/versions"

            response = client.session.get(url, auth=client.auth, headers=client.headers)
            response.raise_for_status()
            subject_versions = response.json()

            result = {
                "schema_id": schema_id,
                "subject_versions": subject_versions,
                "registry": client.config.name,
                "registry_mode": "multi",
                "mcp_protocol_version": "2025-11-25",
            }

            # Add resource links
            result = add_links_to_response(
                result,
                "schema_subjects",
                client.config.name,
                schema_id=schema_id,
            )

            return result
    except Exception as e:
        return create_error_response(str(e), error_code="SCHEMA_SUBJECTS_LOOKUP_FAILED", registry_mode=registry_mode)
