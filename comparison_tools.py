#!/usr/bin/env python3
"""
Comparison Tools Module - Updated with Structured Output

Handles registry comparison operations with structured tool output
support per MCP 2025-06-18 specification.

Provides registry comparison, context comparison, and missing schema detection
with JSON Schema validation and type-safe responses.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from schema_validation import (
    structured_output,
    create_error_response,
    create_success_response
)


@structured_output("compare_registries", fallback_on_error=True)
async def compare_registries_tool(
    source_registry: str,
    target_registry: str,
    registry_manager,
    registry_mode: str,
    include_contexts: bool = True,
    include_configs: bool = True,
) -> Dict[str, Any]:
    """
    Compare two Schema Registry instances and show differences.
    Only available in multi-registry mode.

    Args:
        source_registry: Source registry name
        target_registry: Target registry name
        include_contexts: Include context comparison
        include_configs: Include configuration comparison

    Returns:
        Comparison results with structured validation or error if in single-registry mode
    """
    if registry_mode == "single":
        return create_error_response(
            "Registry comparison is only available in multi-registry mode",
            details={"suggestion": "Set REGISTRY_MODE=multi to enable registry comparison"},
            error_code="SINGLE_REGISTRY_MODE_LIMITATION",
            registry_mode=registry_mode
        )

    try:
        source_client = registry_manager.get_registry(source_registry)
        target_client = registry_manager.get_registry(target_registry)

        if not source_client:
            return create_error_response(
                f"Source registry '{source_registry}' not found",
                error_code="SOURCE_REGISTRY_NOT_FOUND",
                registry_mode=registry_mode
            )
        if not target_client:
            return create_error_response(
                f"Target registry '{target_registry}' not found",
                error_code="TARGET_REGISTRY_NOT_FOUND",
                registry_mode=registry_mode
            )

        comparison = {
            "source_registry": source_registry,
            "target_registry": target_registry,
            "timestamp": datetime.now().isoformat(),
            "differences": {},
            "registry_mode": registry_mode,
            "mcp_protocol_version": "2025-06-18"
        }

        # Compare subjects
        source_subjects = set(source_client.list_subjects() or [])
        target_subjects = set(target_client.list_subjects() or [])

        comparison["differences"]["subjects"] = {
            "only_in_source": list(source_subjects - target_subjects),
            "only_in_target": list(target_subjects - source_subjects),
            "in_both": list(source_subjects & target_subjects),
        }

        # Compare schemas for common subjects
        schema_differences = []
        for subject in source_subjects & target_subjects:
            source_versions = source_client.get_schema_versions(subject) or []
            target_versions = target_client.get_schema_versions(subject) or []

            if source_versions != target_versions:
                schema_differences.append(
                    {
                        "subject": subject,
                        "source_versions": source_versions,
                        "target_versions": target_versions,
                    }
                )

        comparison["differences"]["schemas"] = schema_differences

        # Compare contexts if requested
        if include_contexts:
            source_contexts = set(source_client.list_contexts() or [])
            target_contexts = set(target_client.list_contexts() or [])

            comparison["differences"]["contexts"] = {
                "only_in_source": list(source_contexts - target_contexts),
                "only_in_target": list(target_contexts - source_contexts),
                "in_both": list(source_contexts & target_contexts),
            }

        # Compare configurations if requested
        if include_configs:
            source_config = source_client.get_global_config()
            target_config = target_client.get_global_config()

            comparison["differences"]["global_config"] = {
                "source": source_config,
                "target": target_config,
                "match": source_config == target_config,
            }

        return comparison

    except Exception as e:
        return create_error_response(
            str(e),
            error_code="REGISTRY_COMPARISON_FAILED",
            registry_mode=registry_mode
        )


@structured_output("compare_contexts_across_registries", fallback_on_error=True)
async def compare_contexts_across_registries_tool(
    source_registry: str,
    target_registry: str,
    source_context: str,
    registry_manager,
    registry_mode: str,
    target_context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compare contexts across two registries.
    Only available in multi-registry mode.

    Args:
        source_registry: Source registry name
        target_registry: Target registry name
        source_context: Source context name
        target_context: Target context name (defaults to source_context)

    Returns:
        Context comparison results with structured validation
    """
    if registry_mode == "single":
        return create_error_response(
            "Context comparison across registries is only available in multi-registry mode",
            details={"suggestion": "Set REGISTRY_MODE=multi to enable this feature"},
            error_code="SINGLE_REGISTRY_MODE_LIMITATION",
            registry_mode=registry_mode
        )

    try:
        source_client = registry_manager.get_registry(source_registry)
        target_client = registry_manager.get_registry(target_registry)

        if not source_client:
            return create_error_response(
                f"Source registry '{source_registry}' not found",
                error_code="SOURCE_REGISTRY_NOT_FOUND",
                registry_mode=registry_mode
            )
        if not target_client:
            return create_error_response(
                f"Target registry '{target_registry}' not found",
                error_code="TARGET_REGISTRY_NOT_FOUND",
                registry_mode=registry_mode
            )

        # Use source context for target if not specified
        if target_context is None:
            target_context = source_context

        # Get subjects in each context
        source_subjects = set(source_client.get_subjects(source_context) or [])
        target_subjects = set(target_client.get_subjects(target_context) or [])

        comparison = {
            "source": {
                "registry": source_registry,
                "context": source_context,
                "subject_count": len(source_subjects),
            },
            "target": {
                "registry": target_registry,
                "context": target_context,
                "subject_count": len(target_subjects),
            },
            "differences": {
                "only_in_source": list(source_subjects - target_subjects),
                "only_in_target": list(target_subjects - source_subjects),
                "in_both": list(source_subjects & target_subjects),
            },
            "registry_mode": registry_mode,
            "mcp_protocol_version": "2025-06-18"
        }

        # Compare schemas for common subjects
        schema_differences = []
        for subject in source_subjects & target_subjects:
            source_versions = (
                source_client.get_schema_versions(subject, source_context) or []
            )
            target_versions = (
                target_client.get_schema_versions(subject, target_context) or []
            )

            if source_versions != target_versions:
                schema_differences.append(
                    {
                        "subject": subject,
                        "source_versions": source_versions,
                        "target_versions": target_versions,
                    }
                )

        comparison["schema_differences"] = schema_differences

        return comparison

    except Exception as e:
        return create_error_response(
            str(e),
            error_code="CONTEXT_COMPARISON_FAILED",
            registry_mode=registry_mode
        )


@structured_output("find_missing_schemas", fallback_on_error=True)
async def find_missing_schemas_tool(
    source_registry: str,
    target_registry: str,
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Find schemas that exist in source registry but not in target registry.
    Only available in multi-registry mode.

    Args:
        source_registry: Source registry name
        target_registry: Target registry name
        context: Optional context to limit the search

    Returns:
        List of missing schemas with structured validation
    """
    if registry_mode == "single":
        return create_error_response(
            "Finding missing schemas across registries is only available in multi-registry mode",
            details={"suggestion": "Set REGISTRY_MODE=multi to enable this feature"},
            error_code="SINGLE_REGISTRY_MODE_LIMITATION",
            registry_mode=registry_mode
        )

    try:
        source_client = registry_manager.get_registry(source_registry)
        target_client = registry_manager.get_registry(target_registry)

        if not source_client:
            return create_error_response(
                f"Source registry '{source_registry}' not found",
                error_code="SOURCE_REGISTRY_NOT_FOUND",
                registry_mode=registry_mode
            )
        if not target_client:
            return create_error_response(
                f"Target registry '{target_registry}' not found",
                error_code="TARGET_REGISTRY_NOT_FOUND",
                registry_mode=registry_mode
            )

        # Get subjects based on context
        if context:
            source_subjects = set(source_client.get_subjects(context) or [])
            target_subjects = set(target_client.get_subjects(context) or [])
        else:
            source_subjects = set(source_client.list_subjects() or [])
            target_subjects = set(target_client.list_subjects() or [])

        # Find missing subjects
        missing_subjects = source_subjects - target_subjects

        result = {
            "source_registry": source_registry,
            "target_registry": target_registry,
            "context": context,
            "missing_subjects": list(missing_subjects),
            "missing_count": len(missing_subjects),
            "details": [],
            "registry_mode": registry_mode,
            "mcp_protocol_version": "2025-06-18"
        }

        # Get details for each missing subject
        for subject in missing_subjects:
            versions = source_client.get_schema_versions(subject, context) or []
            latest_schema = None

            if versions:
                latest_schema = source_client.get_schema(
                    subject, str(versions[-1]), context
                )

            result["details"].append(
                {
                    "subject": subject,
                    "versions": versions,
                    "version_count": len(versions),
                    "latest_schema": latest_schema,
                }
            )

        return result

    except Exception as e:
        return create_error_response(
            str(e),
            error_code="MISSING_SCHEMA_SEARCH_FAILED",
            registry_mode=registry_mode
        )
