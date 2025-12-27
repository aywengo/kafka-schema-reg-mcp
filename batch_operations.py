#!/usr/bin/env python3
"""
Application-Level Batch Operations Module - Updated with Structured Output and FastMCP Background Tasks

⚠️  IMPORTANT: These are APPLICATION-LEVEL batch operations, NOT JSON-RPC batching.

    JSON-RPC batching has been disabled per MCP 2025-11-25 specification compliance.
    These functions perform application-level batching by making individual JSON-RPC
    requests for each operation, providing client-side request queuing for performance.

Handles batch cleanup operations for Schema Registry contexts with structured tool output
support per MCP 2025-11-25 specification.

Provides clear_context_batch and clear_multiple_contexts_batch functionality.

Uses FastMCP background tasks API (SEP-1686) for long-running operations.

Migration from JSON-RPC Batching:
- Previously: Single JSON-RPC batch request with multiple operations
- Now: Individual JSON-RPC requests with application-level coordination
- Performance: Maintains efficiency through parallel processing and background tasks
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from fastmcp.dependencies import Progress

from schema_validation import create_error_response, structured_output

# Configure logging
logger = logging.getLogger(__name__)


@structured_output("clear_context_batch", fallback_on_error=True)
async def clear_context_batch_tool(
    context: str,
    registry_manager,
    registry_mode: str,
    registry: Optional[str] = None,
    delete_context_after: bool = True,
    dry_run: bool = True,
    progress: Progress = Progress(),
) -> Dict[str, Any]:
    """Clear all subjects in a context using application-level batch operations.

    ⚠️  APPLICATION-LEVEL BATCHING: This performs application-level batching by
        making individual JSON-RPC requests for each operation. JSON-RPC batching
        has been disabled per MCP 2025-11-25 specification compliance.

    **MEDIUM-DURATION OPERATION** - Uses FastMCP background tasks API (SEP-1686).
    This operation runs asynchronously with progress tracking.

    Performance Notes:
    - Uses parallel processing with ThreadPoolExecutor for efficiency
    - Individual requests maintain protocol compliance
    - Client-side request coordination replaces JSON-RPC batching

    Args:
        context: The context to clear
        registry: The registry to operate on (uses default if not specified)
        delete_context_after: Whether to delete the context after clearing subjects
        dry_run: If True, only simulate the operation without making changes
        progress: FastMCP Progress dependency for progress reporting

    Returns:
        Cleanup results with structured validation
    """
    try:
        # Resolve registry name
        if registry is None:
            # Get first available registry for single-registry compatibility
            available_registries = registry_manager.list_registries()
            if available_registries:
                registry = available_registries[0]  # list_registries() returns list of strings
            else:
                return create_error_response(
                    "No registries available",
                    error_code="NO_REGISTRIES_AVAILABLE",
                    registry_mode=registry_mode,
                )

        # Validate registry exists
        registry_client = registry_manager.get_registry(registry)
        if not registry_client:
            return create_error_response(
                f"Registry '{registry}' not found",
                error_code="REGISTRY_NOT_FOUND",
                registry_mode=registry_mode,
            )

        # Execute cleanup with progress tracking
        return await _execute_clear_context_batch(
            context=context,
            registry=registry,
            registry_manager=registry_manager,
            delete_context_after=delete_context_after,
            dry_run=dry_run,
            progress=progress,
        )

    except Exception as e:
        return create_error_response(str(e), error_code="BATCH_OPERATION_FAILED", registry_mode=registry_mode)


async def _execute_clear_context_batch(
    context: str,
    registry: str,
    registry_manager,
    delete_context_after: bool = True,
    dry_run: bool = True,
    progress: Progress = Progress(),
) -> Dict[str, Any]:
    """Execute the actual context cleanup logic using individual requests.

    Performance Implementation:
    - Uses ThreadPoolExecutor for parallel individual requests
    - Replaces previous JSON-RPC batching with application-level coordination
    - Maintains efficiency while ensuring MCP 2025-06-18 compliance
    """
    start_time = time.time()
    subjects_found = 0
    subjects_deleted = 0
    context_deleted = False
    errors = []

    try:
        # Set total based on number of discrete steps
        # Steps: 1) initialization, 2) fetch subjects, 3) delete subjects (per subject), 4) finalize
        # We'll set total after we know how many subjects we have

        async def update_progress(message: str = ""):
            """Update progress message and increment counter."""
            await progress.set_message(message if message else "Processing...")
            if message:
                logger.info(f"Clear Context Progress: {message}")

        async def increment_progress(message: str = ""):
            """Increment progress counter and update message."""
            await progress.increment()
            await progress.set_message(message if message else "Processing...")
            if message:
                logger.info(f"Clear Context Progress: {message}")

        # Get registry client (registry is already resolved, never None here)
        registry_client = registry_manager.get_registry(registry)

        await update_progress(
            f"Starting cleanup of context '{context}' in registry '{registry}' (individual requests)",
        )

        if not registry_client:
            return {
                "subjects_found": 0,
                "subjects_deleted": 0,
                "context_deleted": False,
                "dry_run": dry_run,
                "duration_seconds": time.time() - start_time,
                "success_rate": 0.0,
                "performance": 0.0,
                "message": f"Registry '{registry}' not found",
                "error": f"Registry '{registry}' not found",
                "registry": registry,
                "batching_method": "application_level",
            }

        # Get all subjects in the context FIRST to determine total progress steps
        # This ensures set_total() is called before any increment() calls
        subjects = registry_client.get_subjects(context)
        if isinstance(subjects, dict) and "error" in subjects:
            subjects = []
        subjects_found = len(subjects)

        # Set total progress steps BEFORE any increments
        # Steps: 1 (registry connected) + 1 (fetch) + subjects_found + 1 (finalize) = 3 + subjects_found
        await progress.set_total(3 + subjects_found)

        await increment_progress("Registry client connected")

        # Check viewonly mode
        viewonly_check = registry_manager.is_viewonly(registry)
        if viewonly_check:
            return {
                "subjects_found": 0,
                "subjects_deleted": 0,
                "context_deleted": False,
                "dry_run": dry_run,
                "duration_seconds": time.time() - start_time,
                "success_rate": 0.0,
                "performance": 0.0,
                "message": f"Registry '{registry}' is in VIEWONLY mode",
                "error": f"Registry '{registry}' is in VIEWONLY mode",
                "registry": registry,
                "batching_method": "application_level",
            }

        await increment_progress("Fetching subjects from context")

        if subjects_found == 0:
            await increment_progress("Context is already empty")
            return {
                "subjects_found": 0,
                "subjects_deleted": 0,
                "context_deleted": False,
                "dry_run": dry_run,
                "duration_seconds": time.time() - start_time,
                "success_rate": 100.0,
                "performance": 0.0,
                "message": f"Context '{context}' is already empty",
                "registry": registry,
                "batching_method": "application_level",
            }

        await update_progress(
            f"Found {subjects_found} subjects to {'delete' if not dry_run else 'analyze'} (using individual requests)",
        )

        if dry_run:
            # Skip all subject deletions for dry run - increment for each skipped subject
            for _ in range(subjects_found):
                await progress.increment()
            await increment_progress(
                f"DRY RUN: Would delete {subjects_found} subjects using individual requests",
            )
            return {
                "subjects_found": subjects_found,
                "subjects_deleted": 0,
                "context_deleted": delete_context_after,
                "dry_run": True,
                "duration_seconds": time.time() - start_time,
                "success_rate": 100.0,
                "performance": 0.0,
                "message": f"DRY RUN: Would delete {subjects_found} subjects from context '{context}' using individual requests",
                "registry": registry,
                "batching_method": "application_level",
            }

        await update_progress(
            f"Starting deletion of {subjects_found} subjects using parallel individual requests",
        )

        # Delete subjects in parallel using individual requests (replaces JSON-RPC batching)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for subject in subjects:
                future = executor.submit(_delete_subject_from_context, registry_client, subject, context)
                futures.append(future)

            total_futures = len(futures)
            for i, future in enumerate(as_completed(futures)):
                try:
                    if future.result():
                        subjects_deleted += 1
                except Exception as e:
                    errors.append(str(e))

                # Increment progress after each deletion completes
                await increment_progress(
                    f"Deleted {subjects_deleted} of {subjects_found} subjects (individual requests)",
                )

        await update_progress("Computing cleanup results")

        # Calculate metrics
        duration = time.time() - start_time
        success_rate = (subjects_deleted / subjects_found * 100) if subjects_found > 0 else 100.0
        performance = subjects_deleted / duration if duration > 0 else 0.0

        # Delete context if requested (not supported by Schema Registry API)
        if delete_context_after and subjects_deleted == subjects_found:
            context_deleted = False  # Context deletion not supported by API
            await update_progress("Context deletion not supported by API")

        await increment_progress(
            f"Cleanup completed - deleted {subjects_deleted} subjects using individual requests",
        )

        return {
            "subjects_found": subjects_found,
            "subjects_deleted": subjects_deleted,
            "context_deleted": context_deleted,
            "dry_run": False,
            "duration_seconds": duration,
            "success_rate": success_rate,
            "performance": performance,
            "message": f"Successfully cleared context '{context}' - deleted {subjects_deleted} subjects using individual requests",
            "errors": errors if errors else None,
            "registry": registry,
            "batching_method": "application_level",
            "compliance_note": "Uses individual requests per MCP 2025-06-18 specification (JSON-RPC batching disabled)",
        }

    except Exception as e:
        return {
            "subjects_found": subjects_found,
            "subjects_deleted": subjects_deleted,
            "context_deleted": False,
            "dry_run": dry_run,
            "duration_seconds": time.time() - start_time,
            "success_rate": 0.0,
            "performance": 0.0,
            "message": f"Batch cleanup failed: {str(e)}",
            "error": str(e),
            "registry": registry,
            "batching_method": "application_level",
        }


def _delete_subject_from_context(registry_client, subject: str, context: Optional[str] = None) -> bool:
    """Helper function to delete a subject from a context using individual request.

    Note: This makes a single HTTP request per subject, replacing previous
    JSON-RPC batching approach for MCP 2025-11-25 compliance.
    """
    try:
        url = registry_client.build_context_url(f"/subjects/{subject}", context)
        response = registry_client.session.delete(url, auth=registry_client.auth, headers=registry_client.headers)
        return response.status_code in [200, 404]  # 404 is OK, subject already deleted
    except Exception:
        return False


@structured_output("clear_multiple_contexts_batch", fallback_on_error=True)
async def clear_multiple_contexts_batch_tool(
    contexts: List[str],
    registry_manager,
    registry_mode: str,
    registry: Optional[str] = None,
    delete_contexts_after: bool = True,
    dry_run: bool = True,
    progress: Progress = Progress(),
) -> Dict[str, Any]:
    """Clear multiple contexts in a registry using application-level batch operations.

    ⚠️  APPLICATION-LEVEL BATCHING: This performs application-level batching by
        making individual JSON-RPC requests for each operation. JSON-RPC batching
        has been disabled per MCP 2025-11-25 specification compliance.

    **LONG-DURATION OPERATION** - Uses FastMCP background tasks API (SEP-1686).
    This operation runs asynchronously with progress tracking.

    Performance Notes:
    - Uses parallel processing with ThreadPoolExecutor for efficiency
    - Individual requests maintain protocol compliance
    - Client-side request coordination replaces JSON-RPC batching

    Args:
        contexts: List of context names to clear
        registry: Registry name to clear contexts from (uses default if not specified)
        delete_contexts_after: Whether to delete the contexts after clearing subjects
        dry_run: If True, only simulate the operation without making changes
        progress: FastMCP Progress dependency for progress reporting

    Returns:
        Cleanup results with structured validation
    """
    try:
        # Resolve registry name
        if registry is None:
            # Get first available registry for single-registry compatibility
            available_registries = registry_manager.list_registries()
            if available_registries:
                registry = available_registries[0]  # list_registries() returns list of strings
            else:
                return create_error_response(
                    "No registries available",
                    error_code="NO_REGISTRIES_AVAILABLE",
                    registry_mode=registry_mode,
                )

        # Validate registry exists
        registry_client = registry_manager.get_registry(registry)
        if not registry_client:
            return create_error_response(
                f"Registry '{registry}' not found",
                error_code="REGISTRY_NOT_FOUND",
                registry_mode=registry_mode,
            )

        # Execute cleanup with progress tracking
        return await _execute_clear_multiple_contexts_batch(
            contexts=contexts,
            registry=registry,
            registry_manager=registry_manager,
            delete_contexts_after=delete_contexts_after,
            dry_run=dry_run,
            progress=progress,
        )

    except Exception as e:
        return create_error_response(str(e), error_code="BATCH_OPERATION_FAILED", registry_mode=registry_mode)


async def _execute_clear_multiple_contexts_batch(
    contexts: List[str],
    registry: str,
    registry_manager,
    delete_contexts_after: bool = True,
    dry_run: bool = True,
    progress: Progress = Progress(),
) -> Dict[str, Any]:
    """Execute the actual multiple contexts cleanup logic using individual requests.

    Performance Implementation:
    - Uses ThreadPoolExecutor for parallel individual requests across contexts
    - Replaces previous JSON-RPC batching with application-level coordination
    - Maintains efficiency while ensuring MCP 2025-06-18 compliance
    """
    start_time = time.time()
    total_subjects_found = 0
    total_subjects_deleted = 0
    contexts_deleted = 0
    errors = []

    try:
        # Set total to number of contexts (one increment per context)
        await progress.set_total(len(contexts))

        async def update_progress(message: str = ""):
            """Update progress message."""
            await progress.set_message(message if message else "Processing...")
            if message:
                logger.info(f"Multi-Context Clear Progress: {message}")

        async def increment_progress(message: str = ""):
            """Increment progress counter and update message."""
            await progress.increment()
            await progress.set_message(message if message else "Processing...")
            if message:
                logger.info(f"Multi-Context Clear Progress: {message}")

        # Get registry client (registry is already resolved, never None here)
        registry_client = registry_manager.get_registry(registry)

        await update_progress(
            f"Starting cleanup of {len(contexts)} contexts in registry '{registry}' (individual requests)",
        )
        if not registry_client:
            return {
                "contexts_processed": 0,
                "total_subjects_found": 0,
                "total_subjects_deleted": 0,
                "contexts_deleted": 0,
                "dry_run": dry_run,
                "duration_seconds": time.time() - start_time,
                "success_rate": 0.0,
                "performance": 0.0,
                "message": f"Registry '{registry}' not found",
                "errors": [f"Registry '{registry}' not found"],
                "batching_method": "application_level",
            }

        await update_progress("Registry client connected")

        # Check viewonly mode
        viewonly_check = registry_manager.is_viewonly(registry)
        if viewonly_check:
            return {
                "contexts_processed": 0,
                "total_subjects_found": 0,
                "total_subjects_deleted": 0,
                "contexts_deleted": 0,
                "dry_run": dry_run,
                "duration_seconds": time.time() - start_time,
                "success_rate": 0.0,
                "performance": 0.0,
                "message": f"Registry '{registry}' is in VIEWONLY mode",
                "errors": [f"Registry '{registry}' is in VIEWONLY mode"],
                "batching_method": "application_level",
            }

        await update_progress("Starting context processing with individual requests")

        # Process each context using individual requests
        total_contexts = len(contexts)
        for i, context in enumerate(contexts, 1):
            try:
                # Get subjects in context
                subjects = registry_client.get_subjects(context)
                if isinstance(subjects, dict) and "error" in subjects:
                    subjects = []
                total_subjects_found += len(subjects)

                await update_progress(
                    f"Processing context {i}/{total_contexts}: '{context}' ({len(subjects)} subjects, individual requests)",
                )

                if dry_run:
                    # Increment progress even for dry run
                    await increment_progress(
                        f"DRY RUN: Would process context '{context}' ({len(subjects)} subjects)",
                    )
                    continue

                # Delete subjects in parallel using individual requests
                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = []
                    for subject in subjects:
                        future = executor.submit(
                            _delete_subject_from_context,
                            registry_client,
                            subject,
                            context,
                        )
                        futures.append(future)

                    # Wait for all deletions to complete
                    context_deleted_count = 0
                    for future in as_completed(futures):
                        try:
                            if future.result():
                                total_subjects_deleted += 1
                                context_deleted_count += 1
                        except Exception as e:
                            errors.append(str(e))

                # Context deletion not supported by Schema Registry API
                if delete_contexts_after:
                    pass  # Context deletion not supported

                # Increment progress after completing each context
                await increment_progress(
                    f"Completed context '{context}' - deleted {context_deleted_count} subjects using individual requests",
                )

            except Exception as e:
                errors.append(f"Error processing context '{context}': {str(e)}")
                # Increment progress even on error to keep counter accurate
                await increment_progress(f"Error processing context '{context}': {str(e)}")

        await update_progress("Computing final results")

        duration = time.time() - start_time
        success_rate = (total_subjects_deleted / total_subjects_found * 100) if total_subjects_found > 0 else 100.0
        subjects_per_second = total_subjects_deleted / duration if duration > 0 else 0.0

        message = (
            f"DRY RUN: Would delete {total_subjects_found} subjects from {len(contexts)} contexts using individual requests"
            if dry_run
            else f"Successfully cleared {len(contexts)} contexts - deleted {total_subjects_deleted}/{total_subjects_found} subjects using individual requests"
        )

        await update_progress(message)

        return {
            "contexts_processed": len(contexts),
            "total_subjects_found": total_subjects_found,
            "total_subjects_deleted": total_subjects_deleted,
            "contexts_deleted": contexts_deleted,
            "dry_run": dry_run,
            "duration_seconds": duration,
            "success_rate": success_rate,
            "performance": subjects_per_second,
            "message": message,
            "errors": errors if errors else None,
            "batching_method": "application_level",
            "compliance_note": "Uses individual requests per MCP 2025-06-18 specification (JSON-RPC batching disabled)",
        }

    except Exception as e:
        return {
            "contexts_processed": 0,
            "total_subjects_found": total_subjects_found,
            "total_subjects_deleted": total_subjects_deleted,
            "contexts_deleted": contexts_deleted,
            "dry_run": dry_run,
            "duration_seconds": time.time() - start_time,
            "success_rate": 0.0,
            "performance": 0.0,
            "message": f"Multi-context cleanup failed: {str(e)}",
            "error": str(e),
            "batching_method": "application_level",
        }
