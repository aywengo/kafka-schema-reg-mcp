#!/usr/bin/env python3
"""
Core Registry Tools Module

Handles basic CRUD operations for Schema Registry.
Provides schema, subject, configuration, and mode management functionality.
"""

import json
from typing import Any, Dict, List, Optional, Union

import aiohttp
import requests

from schema_registry_common import check_readonly_mode as _check_readonly_mode


def build_context_url_legacy(
    base_url: str, schema_registry_url: str, context: Optional[str] = None
) -> str:
    """Build URL with optional context support (legacy function for single-registry mode)."""
    if context and context != ".":
        return f"{schema_registry_url}/contexts/{context}{base_url}"
    return f"{schema_registry_url}{base_url}"


# ===== SCHEMA MANAGEMENT TOOLS =====


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
        Dictionary containing the schema ID
    """
    # Check readonly mode
    readonly_check = _check_readonly_mode(registry_manager, registry)
    if readonly_check:
        return readonly_check

    try:
        if registry_mode == "single":
            # Single-registry mode: use legacy approach
            payload = {
                "schema": json.dumps(schema_definition),
                "schemaType": schema_type,
            }

            url = build_context_url_legacy(
                f"/subjects/{subject}/versions", schema_registry_url, context
            )

            response = requests.post(
                url, data=json.dumps(payload), auth=auth, headers=headers
            )
            response.raise_for_status()
            result = response.json()
            result["registry_mode"] = "single"
            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return {
                    "error": f"Registry '{registry}' not found",
                    "registry_mode": "multi",
                }

            payload = {
                "schema": json.dumps(schema_definition),
                "schemaType": schema_type,
            }

            url = client.build_context_url(f"/subjects/{subject}/versions", context)

            response = requests.post(
                url, data=json.dumps(payload), auth=client.auth, headers=client.headers
            )
            response.raise_for_status()
            result = response.json()
            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            return result
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode}


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
        Dictionary containing schema information
    """
    try:
        if registry_mode == "single":
            # Single-registry mode: use legacy approach
            url = build_context_url_legacy(
                f"/subjects/{subject}/versions/{version}", schema_registry_url, context
            )

            response = requests.get(url, auth=auth, headers=headers)
            response.raise_for_status()
            result = response.json()
            result["registry_mode"] = "single"
            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return {
                    "error": f"Registry '{registry}' not found",
                    "registry_mode": "multi",
                }

            url = client.build_context_url(
                f"/subjects/{subject}/versions/{version}", context
            )

            response = requests.get(url, auth=client.auth, headers=client.headers)
            response.raise_for_status()
            result = response.json()
            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            return result
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode}


def get_schema_versions_tool(
    subject: str,
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None,
    auth=None,
    headers=None,
    schema_registry_url: str = "",
) -> List[int]:
    """
    Get all versions of a schema for a subject.

    Args:
        subject: The subject name
        context: Optional schema context
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        List of version numbers
    """
    try:
        if registry_mode == "single":
            # Single-registry mode: use legacy approach
            url = build_context_url_legacy(
                f"/subjects/{subject}/versions", schema_registry_url, context
            )

            response = requests.get(url, auth=auth, headers=headers)

            # Handle 404 specifically - subject doesn't exist
            if response.status_code == 404:
                return []

            response.raise_for_status()
            return response.json()
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return {"error": f"Registry '{registry}' not found"}

            url = client.build_context_url(f"/subjects/{subject}/versions", context)

            response = requests.get(url, auth=client.auth, headers=client.headers)

            # Handle 404 specifically - subject doesn't exist
            if response.status_code == 404:
                return []

            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"error": str(e)}


def list_subjects_tool(
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None,
    auth=None,
    headers=None,
    schema_registry_url: str = "",
) -> List[str]:
    """
    List all subjects, optionally filtered by context.

    Args:
        context: Optional schema context to filter by
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        List of subject names
    """
    try:
        if registry_mode == "single":
            # Single-registry mode: use legacy approach
            url = build_context_url_legacy("/subjects", schema_registry_url, context)

            response = requests.get(url, auth=auth, headers=headers)
            response.raise_for_status()
            return response.json()
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return {"error": f"Registry '{registry}' not found"}

            return client.get_subjects(context)
    except Exception as e:
        return {"error": str(e)}


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
        Compatibility check result
    """
    try:
        payload = {"schema": json.dumps(schema_definition), "schemaType": schema_type}

        if registry_mode == "single":
            # Single-registry mode: use legacy approach
            url = build_context_url_legacy(
                f"/compatibility/subjects/{subject}/versions/latest",
                schema_registry_url,
                context,
            )

            response = requests.post(
                url, data=json.dumps(payload), auth=auth, headers=headers
            )
            response.raise_for_status()
            result = response.json()
            result["registry_mode"] = "single"
            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return {
                    "error": f"Registry '{registry}' not found",
                    "registry_mode": "multi",
                }

            url = client.build_context_url(
                f"/compatibility/subjects/{subject}/versions/latest", context
            )

            response = requests.post(
                url, data=json.dumps(payload), auth=client.auth, headers=client.headers
            )
            response.raise_for_status()
            result = response.json()
            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            return result
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode}


# ===== CONFIGURATION MANAGEMENT TOOLS =====


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
        Dictionary containing configuration
    """
    try:
        if registry_mode == "single":
            # Single-registry mode: use legacy approach
            url = build_context_url_legacy("/config", schema_registry_url, context)

            response = requests.get(url, auth=auth, headers=standard_headers)
            response.raise_for_status()
            result = response.json()
            result["registry_mode"] = "single"
            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return {
                    "error": f"Registry '{registry}' not found",
                    "registry_mode": "multi",
                }

            url = client.build_context_url("/config", context)

            response = requests.get(
                url, auth=client.auth, headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()
            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            return result
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode}


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
        Updated configuration
    """
    # Check readonly mode
    readonly_check = _check_readonly_mode(registry_manager, registry)
    if readonly_check:
        return readonly_check

    try:
        payload = {"compatibility": compatibility}

        if registry_mode == "single":
            # Single-registry mode: use legacy approach
            url = build_context_url_legacy("/config", schema_registry_url, context)

            response = requests.put(
                url, data=json.dumps(payload), auth=auth, headers=standard_headers
            )
            response.raise_for_status()
            result = response.json()
            result["registry_mode"] = "single"
            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return {
                    "error": f"Registry '{registry}' not found",
                    "registry_mode": "multi",
                }

            url = client.build_context_url("/config", context)

            response = requests.put(
                url,
                data=json.dumps(payload),
                auth=client.auth,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            result = response.json()
            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            return result
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode}


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
        Dictionary containing subject configuration
    """
    try:
        if registry_mode == "single":
            # Single-registry mode: use legacy approach
            url = build_context_url_legacy(
                f"/config/{subject}", schema_registry_url, context
            )

            response = requests.get(url, auth=auth, headers=standard_headers)
            response.raise_for_status()
            result = response.json()
            result["registry_mode"] = "single"
            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return {
                    "error": f"Registry '{registry}' not found",
                    "registry_mode": "multi",
                }

            url = client.build_context_url(f"/config/{subject}", context)

            response = requests.get(
                url, auth=client.auth, headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()
            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            return result
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode}


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
        Updated configuration
    """
    # Check readonly mode
    readonly_check = _check_readonly_mode(registry_manager, registry)
    if readonly_check:
        return readonly_check

    try:
        payload = {"compatibility": compatibility}

        if registry_mode == "single":
            # Single-registry mode: use legacy approach
            url = build_context_url_legacy(
                f"/config/{subject}", schema_registry_url, context
            )

            response = requests.put(
                url, data=json.dumps(payload), auth=auth, headers=standard_headers
            )
            response.raise_for_status()
            result = response.json()
            result["registry_mode"] = "single"
            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return {
                    "error": f"Registry '{registry}' not found",
                    "registry_mode": "multi",
                }

            url = client.build_context_url(f"/config/{subject}", context)

            response = requests.put(
                url,
                data=json.dumps(payload),
                auth=client.auth,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            result = response.json()
            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            return result
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode}


# ===== MODE MANAGEMENT TOOLS =====


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
        Dictionary containing the current mode
    """
    try:
        if registry_mode == "single":
            # Single-registry mode: use legacy approach
            url = build_context_url_legacy("/mode", schema_registry_url, context)

            response = requests.get(url, auth=auth, headers=standard_headers)
            response.raise_for_status()
            result = response.json()
            result["registry_mode"] = "single"
            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return {
                    "error": f"Registry '{registry}' not found",
                    "registry_mode": "multi",
                }

            url = client.build_context_url("/mode", context)

            response = requests.get(
                url, auth=client.auth, headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()
            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            return result
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode}


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
        Updated mode information
    """
    # Check readonly mode
    readonly_check = _check_readonly_mode(registry_manager, registry)
    if readonly_check:
        return readonly_check

    try:
        payload = {"mode": mode}

        if registry_mode == "single":
            # Single-registry mode: use legacy approach
            url = build_context_url_legacy("/mode", schema_registry_url, context)

            response = requests.put(
                url, data=json.dumps(payload), auth=auth, headers=standard_headers
            )
            response.raise_for_status()
            result = response.json()
            result["registry_mode"] = "single"
            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return {
                    "error": f"Registry '{registry}' not found",
                    "registry_mode": "multi",
                }

            url = client.build_context_url("/mode", context)

            response = requests.put(
                url,
                data=json.dumps(payload),
                auth=client.auth,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            result = response.json()
            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            return result
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode}


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
        Dictionary containing the subject mode
    """
    try:
        if registry_mode == "single":
            # Single-registry mode: use legacy approach
            url = build_context_url_legacy(
                f"/mode/{subject}", schema_registry_url, context
            )

            response = requests.get(url, auth=auth, headers=standard_headers)
            response.raise_for_status()
            result = response.json()
            result["registry_mode"] = "single"
            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return {
                    "error": f"Registry '{registry}' not found",
                    "registry_mode": "multi",
                }

            url = client.build_context_url(f"/mode/{subject}", context)

            response = requests.get(
                url, auth=client.auth, headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()
            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            return result
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode}


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
        Updated mode information
    """
    # Check readonly mode
    readonly_check = _check_readonly_mode(registry_manager, registry)
    if readonly_check:
        return readonly_check

    try:
        payload = {"mode": mode}

        if registry_mode == "single":
            # Single-registry mode: use legacy approach
            url = build_context_url_legacy(
                f"/mode/{subject}", schema_registry_url, context
            )

            response = requests.put(
                url, data=json.dumps(payload), auth=auth, headers=standard_headers
            )
            response.raise_for_status()
            result = response.json()
            result["registry_mode"] = "single"
            return result
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return {
                    "error": f"Registry '{registry}' not found",
                    "registry_mode": "multi",
                }

            url = client.build_context_url(f"/mode/{subject}", context)

            response = requests.put(
                url,
                data=json.dumps(payload),
                auth=client.auth,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            result = response.json()
            result["registry"] = client.config.name
            result["registry_mode"] = "multi"
            return result
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode}


# ===== CONTEXT AND SUBJECT MANAGEMENT =====


def list_contexts_tool(
    registry_manager,
    registry_mode: str,
    registry: Optional[str] = None,
    auth=None,
    headers=None,
    schema_registry_url: str = "",
) -> List[str]:
    """
    List all available schema contexts.

    Args:
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        List of context names
    """
    try:
        if registry_mode == "single":
            # Single-registry mode: use legacy approach
            response = requests.get(
                f"{schema_registry_url}/contexts", auth=auth, headers=headers
            )
            response.raise_for_status()
            return response.json()
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return {"error": f"Registry '{registry}' not found"}

            return client.get_contexts()
    except Exception as e:
        return {"error": str(e)}


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
        Success message
    """
    # Check readonly mode
    readonly_check = _check_readonly_mode(registry_manager, registry)
    if readonly_check:
        return readonly_check

    try:
        if registry_mode == "single":
            # Single-registry mode: use legacy approach
            response = requests.post(
                f"{schema_registry_url}/contexts/{context}", auth=auth, headers=headers
            )
            response.raise_for_status()
            return {
                "message": f"Context '{context}' created successfully",
                "registry_mode": "single",
            }
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return {
                    "error": f"Registry '{registry}' not found",
                    "registry_mode": "multi",
                }

            response = requests.post(
                f"{client.config.url}/contexts/{context}",
                auth=client.auth,
                headers=client.headers,
            )
            response.raise_for_status()
            return {
                "message": f"Context '{context}' created successfully",
                "registry": client.config.name,
                "registry_mode": "multi",
            }
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode}


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
        Success message
    """
    # Check readonly mode
    readonly_check = _check_readonly_mode(registry_manager, registry)
    if readonly_check:
        return readonly_check

    try:
        if registry_mode == "single":
            # Single-registry mode: use legacy approach
            response = requests.delete(
                f"{schema_registry_url}/contexts/{context}", auth=auth, headers=headers
            )
            response.raise_for_status()
            return {
                "message": f"Context '{context}' deleted successfully",
                "registry_mode": "single",
            }
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return {
                    "error": f"Registry '{registry}' not found",
                    "registry_mode": "multi",
                }

            response = requests.delete(
                f"{client.config.url}/contexts/{context}",
                auth=client.auth,
                headers=client.headers,
            )
            response.raise_for_status()
            return {
                "message": f"Context '{context}' deleted successfully",
                "registry": client.config.name,
                "registry_mode": "multi",
            }
    except Exception as e:
        return {"error": str(e), "registry_mode": registry_mode}


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
) -> List[int]:
    """
    Delete a subject and all its versions.

    Args:
        subject: The subject name to delete
        context: Optional schema context
        registry: Optional registry name (ignored in single-registry mode)
        permanent: If True, perform a hard delete (removes all metadata including schema ID)

    Returns:
        List of deleted version numbers
    """
    # Check readonly mode
    readonly_check = _check_readonly_mode(registry_manager, registry)
    if readonly_check:
        return readonly_check

    try:
        if registry_mode == "single":
            # Single-registry mode: use legacy approach
            url = build_context_url_legacy(
                f"/subjects/{subject}", schema_registry_url, context
            )
            
            # Add permanent parameter if specified
            if permanent:
                url += "?permanent=true"

            response = requests.delete(url, auth=auth, headers=headers)
            response.raise_for_status()
            return response.json()
        else:
            # Multi-registry mode: use client approach
            client = registry_manager.get_registry(registry)
            if client is None:
                return {"error": f"Registry '{registry}' not found"}

            url = client.build_context_url(f"/subjects/{subject}", context)
            
            # Add permanent parameter if specified
            if permanent:
                url += "?permanent=true"

            # Use aiohttp for async HTTP requests
            async with aiohttp.ClientSession() as session:
                async with session.delete(url, headers=client.headers) as response:
                    response.raise_for_status()
                    return await response.json()
    except Exception as e:
        return {"error": str(e)}
