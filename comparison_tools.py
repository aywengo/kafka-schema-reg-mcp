#!/usr/bin/env python3
"""
Comparison Tools Module - Updated with Resource Linking

Handles registry comparison operations with structured tool output
support per MCP 2025-06-18 specification including resource linking.

Provides registry comparison, context comparison, and missing schema detection
with JSON Schema validation, type-safe responses, and HATEOAS navigation links.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from resource_linking import add_links_to_response
from schema_validation import (
    create_error_response,
    structured_output,
)

if TYPE_CHECKING:
    from fastmcp.server.context import Context


@structured_output("compare_registries", fallback_on_error=True)
async def compare_registries_tool(
    source_registry: str,
    target_registry: str,
    registry_manager,
    registry_mode: str,
    include_contexts: bool = True,
    include_configs: bool = True,
    context: Optional["Context"] = None,
) -> Dict[str, Any]:
    """
    Compare two Schema Registry instances and show differences.
    Only available in multi-registry mode.

    Args:
        source_registry: Source registry name
        target_registry: Target registry name
        include_contexts: Include context comparison
        include_configs: Include configuration comparison
        context: MCP Context for progress reporting

    Returns:
        Comparison results with structured validation and resource links, or error if in single-registry mode
    """
    if registry_mode == "single":
        return create_error_response(
            "Registry comparison is only available in multi-registry mode",
            details={"suggestion": "Set REGISTRY_MODE=multi to enable registry comparison"},
            error_code="SINGLE_REGISTRY_MODE_LIMITATION",
            registry_mode=registry_mode,
        )

    try:
        # Initial setup (0-10%)
        if context:
            await context.info(f"Starting registry comparison: {source_registry} vs {target_registry}")
            await context.report_progress(0.0, 100.0, "Initializing registry comparison")

        source_client = registry_manager.get_registry(source_registry)
        target_client = registry_manager.get_registry(target_registry)

        if not source_client:
            return create_error_response(
                f"Source registry '{source_registry}' not found",
                error_code="SOURCE_REGISTRY_NOT_FOUND",
                registry_mode=registry_mode,
            )
        if not target_client:
            return create_error_response(
                f"Target registry '{target_registry}' not found",
                error_code="TARGET_REGISTRY_NOT_FOUND",
                registry_mode=registry_mode,
            )

        if context:
            await context.report_progress(10.0, 100.0, "Registry clients initialized")

        comparison: Dict[str, Any] = {
            "source_registry": source_registry,
            "target_registry": target_registry,
            "timestamp": datetime.now().isoformat(),
            "differences": {},
            "registry_mode": registry_mode,
            "mcp_protocol_version": "2025-11-25",
        }

        # Compare subjects (10-30%)
        if context:
            await context.info(f"Fetching subjects from source registry: {source_registry}")
            await context.report_progress(15.0, 100.0, f"Fetching subjects from {source_registry}")

        source_subjects = set(source_client.get_subjects() or [])

        if context:
            await context.report_progress(20.0, 100.0, f"Found {len(source_subjects)} subjects in source registry")

        if context:
            await context.info(f"Fetching subjects from target registry: {target_registry}")
            await context.report_progress(25.0, 100.0, f"Fetching subjects from {target_registry}")

        target_subjects = set(target_client.get_subjects() or [])

        if context:
            await context.report_progress(30.0, 100.0, f"Found {len(target_subjects)} subjects in target registry")

        # Build subject comparison (30-35%)
        if context:
            await context.report_progress(30.0, 100.0, "Building subject comparison")

        comparison["differences"]["subjects"] = {
            "only_in_source": list(source_subjects - target_subjects),
            "only_in_target": list(target_subjects - source_subjects),
            "in_both": list(source_subjects & target_subjects),
            "source_total": len(source_subjects),
            "target_total": len(target_subjects),
            "common_count": len(source_subjects & target_subjects),
        }

        if context:
            await context.report_progress(35.0, 100.0, "Subject comparison completed")

        # Compare schemas for common subjects (35-55%)
        common_subjects = source_subjects & target_subjects
        schema_differences = []

        if context:
            await context.info(f"Comparing schemas for {len(common_subjects)} common subjects")
            await context.report_progress(40.0, 100.0, f"Comparing schemas for {len(common_subjects)} common subjects")

        if common_subjects:
            for i, subject in enumerate(common_subjects):
                # Report progress for schema comparison
                if context and len(common_subjects) > 0:
                    progress = 40.0 + (i / len(common_subjects)) * 15.0  # 40% to 55%
                    await context.report_progress(progress, 100.0, f"Comparing schema versions for {subject}")

                source_versions = source_client.get_schema_versions(subject) or []
                target_versions = target_client.get_schema_versions(subject) or []

                if source_versions != target_versions:
                    schema_differences.append(
                        {
                            "subject": subject,
                            "source_versions": source_versions,
                            "target_versions": target_versions,
                            "source_version_count": (len(source_versions) if isinstance(source_versions, list) else 0),
                            "target_version_count": (len(target_versions) if isinstance(target_versions, list) else 0),
                        }
                    )

        if context:
            await context.report_progress(
                55.0, 100.0, f"Found {len(schema_differences)} subjects with schema differences"
            )

        comparison["differences"]["schemas"] = {
            "subjects_with_differences": schema_differences,
            "subjects_with_differences_count": len(schema_differences),
        }

        # Compare contexts if requested (55-70%)
        if include_contexts:
            if context:
                await context.info("Comparing contexts between registries")
                await context.report_progress(60.0, 100.0, "Fetching contexts from source registry")

            source_contexts = set(source_client.get_contexts() or [])

            if context:
                await context.report_progress(65.0, 100.0, f"Found {len(source_contexts)} contexts in source registry")

            target_contexts = set(target_client.get_contexts() or [])

            if context:
                await context.report_progress(70.0, 100.0, f"Found {len(target_contexts)} contexts in target registry")

            comparison["differences"]["contexts"] = {
                "only_in_source": list(source_contexts - target_contexts),
                "only_in_target": list(target_contexts - source_contexts),
                "in_both": list(source_contexts & target_contexts),
                "source_total": len(source_contexts),
                "target_total": len(target_contexts),
                "common_count": len(source_contexts & target_contexts),
            }
        else:
            if context:
                await context.report_progress(70.0, 100.0, "Skipping context comparison")

        # Compare configurations if requested (70-85%)
        if include_configs:
            if context:
                await context.info("Comparing global configurations")
                await context.report_progress(75.0, 100.0, "Fetching global configurations")

            source_config = source_client.get_global_config()
            target_config = target_client.get_global_config()

            # Remove registry-specific fields for comparison
            source_config_clean = {k: v for k, v in source_config.items() if k not in ["registry", "error"]}
            target_config_clean = {k: v for k, v in target_config.items() if k not in ["registry", "error"]}

            if context:
                await context.report_progress(80.0, 100.0, "Analyzing configuration differences")

            comparison["differences"]["global_config"] = {
                "source": source_config,
                "target": target_config,
                "match": source_config_clean == target_config_clean,
                "differences": {
                    k: {
                        "source": source_config_clean.get(k),
                        "target": target_config_clean.get(k),
                    }
                    for k in set(source_config_clean.keys()) | set(target_config_clean.keys())
                    if source_config_clean.get(k) != target_config_clean.get(k)
                },
            }

            if context:
                await context.report_progress(85.0, 100.0, "Configuration comparison completed")
        else:
            if context:
                await context.report_progress(85.0, 100.0, "Skipping configuration comparison")

        # Add summary statistics (85-95%)
        if context:
            await context.report_progress(90.0, 100.0, "Building comparison summary")

        comparison["summary"] = {
            "subjects_only_in_source": len(comparison["differences"]["subjects"]["only_in_source"]),
            "subjects_only_in_target": len(comparison["differences"]["subjects"]["only_in_target"]),
            "subjects_in_both": len(comparison["differences"]["subjects"]["in_both"]),
            "schemas_with_differences": len(schema_differences),
            "registries_match": (
                len(comparison["differences"]["subjects"]["only_in_source"]) == 0
                and len(comparison["differences"]["subjects"]["only_in_target"]) == 0
                and len(schema_differences) == 0
            ),
        }

        # Add resource links (95-100%)
        if context:
            await context.report_progress(95.0, 100.0, "Adding resource links")

        comparison = add_links_to_response(
            comparison,
            "comparison",
            source_registry,
            source_registry=source_registry,
            target_registry=target_registry,
        )

        if context:
            await context.info("Registry comparison completed successfully")
            await context.report_progress(100.0, 100.0, "Registry comparison completed")

        return comparison

    except Exception as e:
        if context:
            await context.error(f"Registry comparison failed: {str(e)}")
        return create_error_response(str(e), error_code="REGISTRY_COMPARISON_FAILED", registry_mode=registry_mode)


@structured_output("compare_contexts_across_registries", fallback_on_error=True)
async def compare_contexts_across_registries_tool(
    source_registry: str,
    target_registry: str,
    source_context: str,
    registry_manager,
    registry_mode: str,
    target_context: Optional[str] = None,
    context: Optional["Context"] = None,
) -> Dict[str, Any]:
    """
    Compare contexts across two registries.
    Only available in multi-registry mode.

    Args:
        source_registry: Source registry name
        target_registry: Target registry name
        source_context: Source context name
        target_context: Target context name (defaults to source_context)
        context: MCP Context for progress reporting

    Returns:
        Context comparison results with structured validation and resource links
    """
    if registry_mode == "single":
        return create_error_response(
            "Context comparison across registries is only available in multi-registry mode",
            details={"suggestion": "Set REGISTRY_MODE=multi to enable this feature"},
            error_code="SINGLE_REGISTRY_MODE_LIMITATION",
            registry_mode=registry_mode,
        )

    try:
        # Initial setup (0-10%)
        if context:
            await context.info(
                f"Starting context comparison: {source_registry}/{source_context} vs "
                f"{target_registry}/{target_context or source_context}"
            )
            await context.report_progress(0.0, 100.0, "Initializing context comparison")

        source_client = registry_manager.get_registry(source_registry)
        target_client = registry_manager.get_registry(target_registry)

        if not source_client:
            return create_error_response(
                f"Source registry '{source_registry}' not found",
                error_code="SOURCE_REGISTRY_NOT_FOUND",
                registry_mode=registry_mode,
            )
        if not target_client:
            return create_error_response(
                f"Target registry '{target_registry}' not found",
                error_code="TARGET_REGISTRY_NOT_FOUND",
                registry_mode=registry_mode,
            )

        # Use source context for target if not specified
        if target_context is None:
            target_context = source_context

        if context:
            await context.report_progress(10.0, 100.0, "Registry clients initialized")

        # Get subjects from source context (10-30%)
        if context:
            await context.info(f"Fetching subjects from source context: {source_registry}/{source_context}")
            await context.report_progress(15.0, 100.0, f"Fetching subjects from {source_registry}/{source_context}")

        source_subjects = set(source_client.get_subjects(source_context) or [])

        if context:
            await context.report_progress(25.0, 100.0, f"Found {len(source_subjects)} subjects in source context")

        # Get subjects from target context (30-50%)
        if context:
            await context.info(f"Fetching subjects from target context: {target_registry}/{target_context}")
            await context.report_progress(35.0, 100.0, f"Fetching subjects from {target_registry}/{target_context}")

        target_subjects = set(target_client.get_subjects(target_context) or [])

        if context:
            await context.report_progress(45.0, 100.0, f"Found {len(target_subjects)} subjects in target context")

        # Build comparison structure (50-60%)
        if context:
            await context.report_progress(50.0, 100.0, "Building comparison structure")

        comparison: Dict[str, Any] = {
            "source": {
                "registry": source_registry,
                "context": source_context,
                "subject_count": len(source_subjects),
                "subjects": list(source_subjects),
            },
            "target": {
                "registry": target_registry,
                "context": target_context,
                "subject_count": len(target_subjects),
                "subjects": list(target_subjects),
            },
            "differences": {
                "only_in_source": list(source_subjects - target_subjects),
                "only_in_target": list(target_subjects - source_subjects),
                "in_both": list(source_subjects & target_subjects),
            },
            "timestamp": datetime.now().isoformat(),
            "registry_mode": registry_mode,
            "mcp_protocol_version": "2025-11-25",
        }

        if context:
            await context.report_progress(60.0, 100.0, "Analyzing subject differences")

        # Compare schemas for common subjects (60-90%)
        common_subjects = source_subjects & target_subjects
        schema_differences = []

        if context:
            await context.info(f"Comparing schemas for {len(common_subjects)} common subjects")
            await context.report_progress(65.0, 100.0, f"Comparing schemas for {len(common_subjects)} common subjects")

        if common_subjects:
            for i, subject in enumerate(common_subjects):
                # Report progress for schema comparison
                if context and len(common_subjects) > 0:
                    progress = 65.0 + (i / len(common_subjects)) * 20.0  # 65% to 85%
                    await context.report_progress(progress, 100.0, f"Comparing schema versions for {subject}")

                source_versions = source_client.get_schema_versions(subject, source_context) or []
                target_versions = target_client.get_schema_versions(subject, target_context) or []

                if source_versions != target_versions:
                    schema_differences.append(
                        {
                            "subject": subject,
                            "source_versions": source_versions,
                            "target_versions": target_versions,
                            "source_version_count": (len(source_versions) if isinstance(source_versions, list) else 0),
                            "target_version_count": (len(target_versions) if isinstance(target_versions, list) else 0),
                        }
                    )

        if context:
            await context.report_progress(
                85.0, 100.0, f"Found {len(schema_differences)} subjects with version differences"
            )

        comparison["schema_differences"] = {
            "subjects_with_differences": schema_differences,
            "count": len(schema_differences),
        }

        # Add summary (90-95%)
        if context:
            await context.report_progress(90.0, 100.0, "Building comparison summary")

        comparison["summary"] = {
            "contexts_match": (
                len(comparison["differences"]["only_in_source"]) == 0
                and len(comparison["differences"]["only_in_target"]) == 0
                and len(schema_differences) == 0
            ),
            "subjects_only_in_source": len(comparison["differences"]["only_in_source"]),
            "subjects_only_in_target": len(comparison["differences"]["only_in_target"]),
            "subjects_in_both": len(comparison["differences"]["in_both"]),
            "schemas_with_version_differences": len(schema_differences),
        }

        # Add resource links (95-100%)
        if context:
            await context.report_progress(95.0, 100.0, "Adding resource links")

        comparison = add_links_to_response(
            comparison,
            "comparison",
            source_registry,
            source_registry=source_registry,
            target_registry=target_registry,
        )

        if context:
            await context.info("Context comparison completed successfully")
            await context.report_progress(100.0, 100.0, "Context comparison completed")

        return comparison

    except Exception as e:
        if context:
            await context.error(f"Context comparison failed: {str(e)}")
        return create_error_response(str(e), error_code="CONTEXT_COMPARISON_FAILED", registry_mode=registry_mode)


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
        List of missing schemas with structured validation and resource links
    """
    if registry_mode == "single":
        return create_error_response(
            "Finding missing schemas across registries is only available in multi-registry mode",
            details={"suggestion": "Set REGISTRY_MODE=multi to enable this feature"},
            error_code="SINGLE_REGISTRY_MODE_LIMITATION",
            registry_mode=registry_mode,
        )

    try:
        source_client = registry_manager.get_registry(source_registry)
        target_client = registry_manager.get_registry(target_registry)

        if not source_client:
            return create_error_response(
                f"Source registry '{source_registry}' not found",
                error_code="SOURCE_REGISTRY_NOT_FOUND",
                registry_mode=registry_mode,
            )
        if not target_client:
            return create_error_response(
                f"Target registry '{target_registry}' not found",
                error_code="TARGET_REGISTRY_NOT_FOUND",
                registry_mode=registry_mode,
            )

        # Get subjects based on context
        if context:
            source_subjects = set(source_client.get_subjects(context) or [])
            target_subjects = set(target_client.get_subjects(context) or [])
        else:
            source_subjects = set(source_client.get_subjects() or [])
            target_subjects = set(target_client.get_subjects() or [])

        # Find missing subjects
        missing_subjects = source_subjects - target_subjects

        result: Dict[str, Any] = {
            "source_registry": source_registry,
            "target_registry": target_registry,
            "context": context,
            "missing_subjects": list(missing_subjects),
            "missing_count": len(missing_subjects),
            "source_subject_count": len(source_subjects),
            "target_subject_count": len(target_subjects),
            "details": [],
            "timestamp": datetime.now().isoformat(),
            "registry_mode": registry_mode,
            "mcp_protocol_version": "2025-11-25",
        }

        # Ensure details is treated as a list
        details_list: List[Dict[str, Any]] = result["details"]

        # Get details for each missing subject
        for subject in missing_subjects:
            try:
                versions = source_client.get_schema_versions(subject, context) or []
                latest_schema = None

                if versions:
                    latest_version = max(versions) if isinstance(versions, list) else "latest"
                    latest_schema = source_client.get_schema(subject, str(latest_version), context)

                details_list.append(
                    {
                        "subject": subject,
                        "versions": versions,
                        "version_count": (len(versions) if isinstance(versions, list) else 0),
                        "latest_version": latest_version if versions else None,
                        "latest_schema_id": (
                            latest_schema.get("id") if latest_schema and isinstance(latest_schema, dict) else None
                        ),
                        "schema_type": (
                            latest_schema.get("schemaType", "AVRO")
                            if latest_schema and isinstance(latest_schema, dict)
                            else None
                        ),
                    }
                )
            except Exception as e:
                # If we can't get details for a subject, still include it in the list
                details_list.append(
                    {
                        "subject": subject,
                        "versions": [],
                        "version_count": 0,
                        "error": f"Failed to get subject details: {str(e)}",
                    }
                )

        # Update result with processed details
        result["details"] = details_list

        # Add summary information
        result["summary"] = {
            "migration_needed": len(missing_subjects) > 0,
            "total_versions_to_migrate": sum(detail.get("version_count", 0) for detail in details_list),
            "subjects_with_multiple_versions": len(
                [detail for detail in details_list if detail.get("version_count", 0) > 1]
            ),
        }

        # Add resource links
        result = add_links_to_response(
            result,
            "comparison",
            source_registry,
            source_registry=source_registry,
            target_registry=target_registry,
        )

        return result

    except Exception as e:
        return create_error_response(
            str(e),
            error_code="MISSING_SCHEMA_SEARCH_FAILED",
            registry_mode=registry_mode,
        )
