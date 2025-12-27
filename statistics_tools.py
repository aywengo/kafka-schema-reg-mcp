#!/usr/bin/env python3
"""
Statistics Tools Module - Updated with Structured Output and FastMCP Background Tasks

Handles counting and statistics operations for Schema Registry with structured tool output
support per MCP 2025-11-25 specification.

Provides counting for contexts, schemas, versions, and comprehensive registry statistics
with JSON Schema validation and type-safe responses.

Uses FastMCP background tasks API (SEP-1686) for long-running operations.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastmcp.dependencies import Progress

from schema_registry_common import get_default_client
from schema_validation import (
    create_error_response,
    structured_output,
)


@structured_output("count_contexts", fallback_on_error=True)
def count_contexts_tool(registry_manager, registry_mode: str, registry: Optional[str] = None) -> Dict[str, Any]:
    """
    Count the number of contexts in a registry.

    Args:
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Dictionary containing context count and details with registry metadata and structured validation
    """
    try:
        if registry_mode == "single":
            client = get_default_client(registry_manager)
        else:
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode=registry_mode,
                )

        contexts = client.get_contexts()
        if isinstance(contexts, dict) and "error" in contexts:
            return create_error_response(
                f"Failed to get contexts: {contexts.get('error')}",
                error_code="CONTEXTS_RETRIEVAL_FAILED",
                registry_mode=registry_mode,
            )

        # Get registry metadata
        metadata = client.get_server_metadata()

        result = {
            "registry": (client.config.name if hasattr(client.config, "name") else "default"),
            "count": len(contexts),
            "scope": "contexts",
            "contexts": contexts,
            "counted_at": datetime.now().isoformat(),
            "registry_mode": registry_mode,
            "mcp_protocol_version": "2025-11-25",
        }

        # Add metadata information, but preserve the scope field
        metadata_copy = metadata.copy()
        if "scope" in metadata_copy:
            # Preserve the simple string scope, but add server scope info separately
            metadata_copy["server_scope"] = metadata_copy.pop("scope")
        result.update(metadata_copy)

        return result
    except Exception as e:
        return create_error_response(str(e), error_code="CONTEXT_COUNT_FAILED", registry_mode=registry_mode)


@structured_output("count_schemas", fallback_on_error=True)
def count_schemas_tool(
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Count the number of schemas in a context or registry.

    Args:
        context: Optional schema context
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Dictionary containing schema count and details with registry metadata and structured validation
    """
    try:
        if registry_mode == "single":
            client = get_default_client(registry_manager)
        else:
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode=registry_mode,
                )

        subjects = client.get_subjects(context)
        if isinstance(subjects, dict) and "error" in subjects:
            return create_error_response(
                f"Failed to get subjects: {subjects.get('error')}",
                error_code="SUBJECTS_RETRIEVAL_FAILED",
                registry_mode=registry_mode,
            )

        # Get registry metadata
        metadata = client.get_server_metadata()

        result = {
            "registry": (client.config.name if hasattr(client.config, "name") else "default"),
            "context": context or "default",
            "count": len(subjects),
            "scope": "schemas",
            "schemas": subjects,
            "counted_at": datetime.now().isoformat(),
            "registry_mode": registry_mode,
            "mcp_protocol_version": "2025-11-25",
        }

        # Add metadata information, but preserve the scope field
        metadata_copy = metadata.copy()
        if "scope" in metadata_copy:
            # Preserve the simple string scope, but add server scope info separately
            metadata_copy["server_scope"] = metadata_copy.pop("scope")
        result.update(metadata_copy)

        return result
    except Exception as e:
        return create_error_response(str(e), error_code="SCHEMA_COUNT_FAILED", registry_mode=registry_mode)


@structured_output("count_schema_versions", fallback_on_error=True)
def count_schema_versions_tool(
    subject: str,
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Count the number of versions for a specific schema.

    Args:
        subject: The subject name
        context: Optional schema context
        registry: Optional registry name (ignored in single-registry mode)

    Returns:
        Dictionary containing version count and details with registry metadata and structured validation
    """
    try:
        if registry_mode == "single":
            client = get_default_client(registry_manager)
        else:
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode=registry_mode,
                )

        # Import the function here to avoid circular imports
        from kafka_schema_registry_unified_mcp import get_schema_versions

        versions = get_schema_versions(subject, context, registry)
        if isinstance(versions, dict) and "error" in versions:
            return create_error_response(
                f"Failed to get schema versions: {versions.get('error')}",
                error_code="SCHEMA_VERSIONS_RETRIEVAL_FAILED",
                registry_mode=registry_mode,
            )

        # Get registry metadata
        metadata = client.get_server_metadata()

        result = {
            "registry": (client.config.name if hasattr(client.config, "name") else "default"),
            "context": context or "default",
            "subject": subject,
            "count": len(versions),
            "scope": "versions",
            "versions": versions,
            "counted_at": datetime.now().isoformat(),
            "registry_mode": registry_mode,
            "mcp_protocol_version": "2025-11-25",
        }

        # Add metadata information, but preserve the scope field
        metadata_copy = metadata.copy()
        if "scope" in metadata_copy:
            # Preserve the simple string scope, but add server scope info separately
            metadata_copy["server_scope"] = metadata_copy.pop("scope")
        result.update(metadata_copy)

        return result
    except Exception as e:
        return create_error_response(str(e), error_code="VERSION_COUNT_FAILED", registry_mode=registry_mode)


@structured_output("get_registry_statistics", fallback_on_error=True)
def get_registry_statistics_tool(
    registry_manager,
    registry_mode: str,
    registry: Optional[str] = None,
    include_context_details: bool = True,
) -> Dict[str, Any]:
    """
    Get comprehensive statistics about a registry.

    Args:
        registry: Optional registry name (ignored in single-registry mode)
        include_context_details: Whether to include detailed context statistics

    Returns:
        Dictionary containing registry statistics with metadata and structured validation
    """
    try:
        if registry_mode == "single":
            client = get_default_client(registry_manager)
        else:
            client = registry_manager.get_registry(registry)
            if client is None:
                return create_error_response(
                    f"Registry '{registry}' not found",
                    error_code="REGISTRY_NOT_FOUND",
                    registry_mode=registry_mode,
                )

        # Get all contexts
        contexts = client.get_contexts()
        if isinstance(contexts, dict) and "error" in contexts:
            return create_error_response(
                f"Failed to get contexts: {contexts.get('error')}",
                error_code="CONTEXTS_RETRIEVAL_FAILED",
                registry_mode=registry_mode,
            )

        total_schemas = 0
        total_versions = 0
        context_stats = []

        # Import the function here to avoid circular imports
        from kafka_schema_registry_unified_mcp import get_schema_versions

        # Get statistics for each context
        for context in contexts:
            subjects = client.get_subjects(context)
            if isinstance(subjects, dict) and "error" in subjects:
                continue

            context_schemas = len(subjects)
            context_versions = 0

            # Count versions for each subject
            for subject in subjects:
                versions = get_schema_versions(subject, context, registry)
                if not isinstance(versions, dict):
                    context_versions += len(versions)

            total_schemas += context_schemas
            total_versions += context_versions

            if include_context_details:
                context_stats.append(
                    {
                        "name": context,
                        "subject_count": context_schemas,
                        "schema_count": context_versions,
                    }
                )

        # Get default context stats
        default_subjects = client.get_subjects()
        if not isinstance(default_subjects, dict):
            default_schemas = len(default_subjects)
            default_versions = 0

            for subject in default_subjects:
                versions = get_schema_versions(subject, None, registry)
                if not isinstance(versions, dict):
                    default_versions += len(versions)

            total_schemas += default_schemas
            total_versions += default_versions

            if include_context_details:
                context_stats.append(
                    {
                        "name": "default",
                        "subject_count": default_schemas,
                        "schema_count": default_versions,
                    }
                )

        # Get registry metadata
        metadata = client.get_server_metadata()

        result = {
            "registry": (client.config.name if hasattr(client.config, "name") else "default"),
            "total_contexts": len(contexts),
            "total_subjects": total_schemas,
            "total_schemas": total_versions,
            "contexts": context_stats if include_context_details else None,
            "generated_at": datetime.now().isoformat(),
            "registry_mode": registry_mode,
            "mcp_protocol_version": "2025-11-25",
        }

        # Add metadata information
        result.update(metadata)

        return result
    except Exception as e:
        return create_error_response(str(e), error_code="REGISTRY_STATISTICS_FAILED", registry_mode=registry_mode)


# ===== OPTIMIZED ASYNC STATISTICS FUNCTIONS =====


async def _count_schemas_async(
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None,
    progress: Progress = Progress(),
) -> Dict[str, Any]:
    """
    Async version of count_schemas_tool with better performance.
    Uses parallel API calls when counting multiple contexts.
    Includes registry metadata information.

    Uses FastMCP Progress dependency for progress reporting.
    """
    try:
        if registry_mode == "single":
            client = get_default_client(registry_manager)
        else:
            client = registry_manager.get_registry(registry)
            if client is None:
                return {"error": f"Registry '{registry}' not found"}

        # Get registry metadata
        metadata = client.get_server_metadata()

        if context:
            # Single context - direct call
            await progress.set_message(f"Counting schemas in context '{context}'")
            subjects = client.get_subjects(context)
            if isinstance(subjects, dict) and "error" in subjects:
                return subjects

            await progress.set_total(1)
            await progress.increment()

            result = {
                "registry": (client.config.name if hasattr(client.config, "name") else "default"),
                "context": context,
                "count": len(subjects),  # Use 'count' to match schema
                "scope": "schemas",  # Add scope field as string
                "total_schemas": len(subjects),
                "schemas": subjects,
                "counted_at": datetime.now(timezone.utc).isoformat(),
            }

            # Add metadata information, but preserve the scope field
            metadata_copy = metadata.copy()
            if "scope" in metadata_copy:
                # Preserve the simple string scope, but add server scope info separately
                metadata_copy["server_scope"] = metadata_copy.pop("scope")
            result.update(metadata_copy)
            return result
        else:
            # All contexts - parallel execution
            await progress.set_message("Getting contexts list")
            contexts = client.get_contexts()
            if isinstance(contexts, dict) and "error" in contexts:
                return contexts

            total_contexts = len(contexts) + 1  # +1 for default context
            await progress.set_total(total_contexts)
            await progress.set_message(f"Counting schemas across {total_contexts} contexts")

            total_schemas = 0
            all_schemas = {}

            # Parallel execution for better performance
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_context = {executor.submit(client.get_subjects, ctx): ctx for ctx in contexts}

                # Add default context
                future_to_context[executor.submit(client.get_subjects, None)] = "default"

                for future in as_completed(future_to_context):
                    ctx = future_to_context[future]
                    try:
                        subjects = future.result()
                        if not isinstance(subjects, dict):
                            all_schemas[ctx] = subjects
                            total_schemas += len(subjects)
                        await progress.increment()
                        await progress.set_message(
                            f"Processed context '{ctx}' ({len(subjects) if not isinstance(subjects, dict) else 0} schemas)"
                        )
                    except Exception as e:
                        all_schemas[ctx] = {"error": str(e)}
                        await progress.increment()

            result = {
                "registry": (client.config.name if hasattr(client.config, "name") else "default"),
                "count": total_schemas,  # Use 'count' to match schema
                "scope": "schemas",  # Add scope field as string
                "total_schemas": total_schemas,
                "schemas_by_context": all_schemas,
                "contexts_analyzed": len(all_schemas),
                "counted_at": datetime.now(timezone.utc).isoformat(),
            }

            # Add metadata information, but preserve the scope field
            metadata_copy = metadata.copy()
            if "scope" in metadata_copy:
                # Preserve the simple string scope, but add server scope info separately
                metadata_copy["server_scope"] = metadata_copy.pop("scope")
            result.update(metadata_copy)
            return result
    except Exception as e:
        return {"error": str(e)}


@structured_output("count_schemas_task_queue", fallback_on_error=True)
async def count_schemas_task_queue_tool(
    registry_manager,
    registry_mode: str,
    context: Optional[str] = None,
    registry: Optional[str] = None,
    progress: Progress = Progress(),
) -> Dict[str, Any]:
    """
    Background task version of count_schemas for better performance on large registries.
    Uses FastMCP background tasks API (SEP-1686) for async execution with progress tracking.

    Returns:
        Schema count results with structured validation
    """
    try:
        return await _count_schemas_async(
            registry_manager=registry_manager,
            registry_mode=registry_mode,
            context=context,
            registry=registry,
            progress=progress,
        )
    except Exception as e:
        return create_error_response(str(e), error_code="SCHEMA_COUNT_FAILED", registry_mode=registry_mode)


async def _get_registry_statistics_async(
    registry_manager,
    registry_mode: str,
    registry: Optional[str] = None,
    include_context_details: bool = True,
    progress: Progress = Progress(),
) -> Dict[str, Any]:
    """
    Async version of get_registry_statistics_tool with parallel execution.
    Uses FastMCP Progress dependency for progress reporting.
    """
    try:
        if registry_mode == "single":
            client = get_default_client(registry_manager)
        else:
            client = registry_manager.get_registry(registry)
            if client is None:
                return {"error": f"Registry '{registry}' not found"}

        # Get all contexts
        await progress.set_message("Getting contexts list")
        contexts = client.get_contexts()
        if isinstance(contexts, dict) and "error" in contexts:
            return contexts

        total_contexts = len(contexts) + 1  # +1 for default context
        await progress.set_total(total_contexts)
        await progress.set_message(f"Analyzing {total_contexts} contexts")

        total_schemas = 0
        total_versions = 0
        context_stats = []

        # Parallel execution for better performance
        with ThreadPoolExecutor(max_workers=8) as executor:
            # Submit all context analysis tasks
            future_to_context = {}

            # Add all contexts
            for context in contexts:
                future = executor.submit(_analyze_context_parallel, client, context, registry)
                future_to_context[future] = context

            # Add default context
            future = executor.submit(_analyze_context_parallel, client, None, registry)
            future_to_context[future] = "default"

            # Collect results
            completed = 0
            total_contexts = len(future_to_context)

            for future in as_completed(future_to_context):
                context = future_to_context[future]
                try:
                    context_result = future.result()

                    if not isinstance(context_result, dict) or "error" not in context_result:
                        total_schemas += context_result.get("schemas", 0)
                        total_versions += context_result.get("versions", 0)

                        if include_context_details:
                            context_stats.append(
                                {
                                    "context": context,
                                    "schemas": context_result.get("schemas", 0),
                                    "versions": context_result.get("versions", 0),
                                }
                            )

                    # Update progress
                    completed += 1
                    await progress.increment()
                    await progress.set_message(f"Analyzed {completed}/{total_contexts} contexts")

                except Exception as e:
                    if include_context_details:
                        context_stats.append({"context": context, "error": str(e)})

        await progress.set_message("Finalizing statistics")

        # Get registry metadata
        metadata = client.get_server_metadata()

        result = {
            "registry": (client.config.name if hasattr(client.config, "name") else "default"),
            "total_contexts": len(contexts),
            "total_schemas": total_schemas,
            "total_versions": total_versions,
            "average_versions_per_schema": round(total_versions / max(total_schemas, 1), 2),
            "contexts": context_stats if include_context_details else None,
            "counted_at": datetime.now().isoformat(),
        }

        # Add metadata information
        result.update(metadata)

        await progress.set_message("Statistics complete")

        return result

    except Exception as e:
        return {"error": str(e)}


def _analyze_context_parallel(client, context: Optional[str], registry: Optional[str]) -> Dict[str, Any]:
    """
    Analyze a single context in parallel execution.
    Returns schema and version counts for the context.
    """
    try:
        subjects = client.get_subjects(context)
        if isinstance(subjects, dict) and "error" in subjects:
            return {"error": subjects["error"]}

        schema_count = len(subjects)
        version_count = 0

        # Use ThreadPoolExecutor for version counting too
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Import here to avoid circular imports
            from kafka_schema_registry_unified_mcp import get_schema_versions

            futures = [executor.submit(get_schema_versions, subject, context, registry) for subject in subjects]

            for future in as_completed(futures):
                try:
                    versions = future.result()
                    if not isinstance(versions, dict):
                        version_count += len(versions)
                except Exception:
                    # Skip failed version counts
                    pass

        return {"schemas": schema_count, "versions": version_count}

    except Exception as e:
        return {"error": str(e)}


@structured_output("get_registry_statistics_task_queue", fallback_on_error=True)
async def get_registry_statistics_task_queue_tool(
    registry_manager,
    registry_mode: str,
    registry: Optional[str] = None,
    include_context_details: bool = True,
    progress: Progress = Progress(),
) -> Dict[str, Any]:
    """
    Background task version of get_registry_statistics for better performance.
    Uses FastMCP background tasks API (SEP-1686) for async execution with progress tracking.

    Returns:
        Registry statistics with structured validation
    """
    try:
        return await _get_registry_statistics_async(
            registry_manager=registry_manager,
            registry_mode=registry_mode,
            registry=registry,
            include_context_details=include_context_details,
            progress=progress,
        )
    except Exception as e:
        return create_error_response(str(e), error_code="REGISTRY_STATISTICS_FAILED", registry_mode=registry_mode)
