#!/usr/bin/env python3
"""
Application-Level Batch Operations Module - Updated with Structured Output

⚠️  IMPORTANT: These are APPLICATION-LEVEL batch operations, NOT JSON-RPC batching.

    JSON-RPC batching has been disabled per MCP 2025-06-18 specification compliance.
    These functions perform application-level batching by making individual JSON-RPC
    requests for each operation, providing client-side request queuing for performance.

Handles batch cleanup operations for Schema Registry contexts with structured tool output
support per MCP 2025-06-18 specification.

Provides clear_context_batch and clear_multiple_contexts_batch functionality.

Migration from JSON-RPC Batching:
- Previously: Single JSON-RPC batch request with multiple operations
- Now: Individual JSON-RPC requests with application-level coordination
- Performance: Maintains efficiency through parallel processing and task queuing
"""

import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from schema_validation import create_error_response, structured_output
from task_management import TaskStatus, TaskType, task_manager

# Configure logging
logger = logging.getLogger(__name__)


@structured_output("clear_context_batch", fallback_on_error=True)
def clear_context_batch_tool(
    context: str,
    registry_manager,
    registry_mode: str,
    registry: Optional[str] = None,
    delete_context_after: bool = True,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Clear all subjects in a context using application-level batch operations.

    ⚠️  APPLICATION-LEVEL BATCHING: This performs application-level batching by
        making individual JSON-RPC requests for each operation. JSON-RPC batching
        has been disabled per MCP 2025-06-18 specification compliance.

    **MEDIUM-DURATION OPERATION** - Uses task queue pattern.
    This operation runs asynchronously and returns a task_id immediately.
    Use get_task_status(task_id) to monitor progress and get results.

    Performance Notes:
    - Uses parallel processing with ThreadPoolExecutor for efficiency
    - Individual requests maintain protocol compliance
    - Client-side request coordination replaces JSON-RPC batching

    Args:
        context: The context to clear
        registry: The registry to operate on (uses default if not specified)
        delete_context_after: Whether to delete the context after clearing subjects
        dry_run: If True, only simulate the operation without making changes

    Returns:
        Task information with task_id for monitoring progress with structured validation
    """
    try:
        # Resolve registry name BEFORE creating task (critical for task lookup)
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

        # Create async task with resolved registry name
        task = task_manager.create_task(
            TaskType.CLEANUP,
            metadata={
                "operation": "clear_context_batch",
                "context": context,
                "registry": registry,  # Now always a resolved string, never None
                "delete_context_after": delete_context_after,
                "dry_run": dry_run,
                "batching_type": "application_level",  # For clarity
                "jsonrpc_batching": False,  # Explicitly disabled
            },
        )

        # Start async execution
        try:
            # Check if there's a running event loop
            asyncio.get_running_loop()
            asyncio.create_task(
                task_manager.execute_task(
                    task,
                    _execute_clear_context_batch,
                    context=context,
                    registry=registry,
                    registry_manager=registry_manager,
                    delete_context_after=delete_context_after,
                    dry_run=dry_run,
                )
            )
        except RuntimeError:
            # No running event loop, use thread pool to run the task
            def run_task():
                asyncio.run(
                    task_manager.execute_task(
                        task,
                        _execute_clear_context_batch,
                        context=context,
                        registry=registry,
                        registry_manager=registry_manager,
                        delete_context_after=delete_context_after,
                        dry_run=dry_run,
                    )
                )

            thread = threading.Thread(target=run_task)
            thread.start()

        # Return structured response
        result = {
            "message": "Context cleanup started as async task (application-level batching)",
            "task_id": task.id,
            "task": task.to_dict(),
            "operation_info": {
                "operation": "clear_context_batch",
                "expected_duration": "medium",
                "async_pattern": "task_queue",
                "batching_type": "application_level",
                "jsonrpc_batching_disabled": True,
                "guidance": "Long-running operation using individual requests. Returns task_id immediately. Use get_task_status() to monitor progress.",
                "registry_mode": registry_mode,
                "performance_note": "Uses parallel individual requests instead of JSON-RPC batching for MCP 2025-06-18 compliance",
            },
            "operation": "clear_context_batch",
            "dry_run": dry_run,
            "total_items": 1,  # One context
            "successful": 0,  # Will be updated by task
            "failed": 0,  # Will be updated by task
            "registry_mode": registry_mode,
            "mcp_protocol_version": "2025-06-18",
        }

        return result

    except Exception as e:
        return create_error_response(str(e), error_code="BATCH_OPERATION_FAILED", registry_mode=registry_mode)


def _execute_clear_context_batch(
    context: str,
    registry: str,
    registry_manager,
    delete_context_after: bool = True,
    dry_run: bool = True,
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
        # Get the current task ID from task manager for progress updates
        current_task = None
        for task in task_manager.list_tasks(status=TaskStatus.RUNNING):
            if (
                task.metadata
                and task.metadata.get("operation") == "clear_context_batch"
                and task.metadata.get("context") == context
                and task.metadata.get("registry") == registry
            ):
                current_task = task
                break

        def update_progress(progress: float, message: str = ""):
            if current_task:
                task_manager.update_progress(current_task.id, progress)
            if message:
                logger.info(f"Clear Context Progress {progress:.1f}%: {message}")

        # Get registry client (registry is already resolved, never None here)
        registry_client = registry_manager.get_registry(registry)

        update_progress(
            5.0,
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

        update_progress(10.0, "Registry client connected")

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

        update_progress(20.0, "Fetching subjects from context")

        # Get all subjects in the context
        subjects = registry_client.get_subjects(context)
        if isinstance(subjects, dict) and "error" in subjects:
            subjects = []
        subjects_found = len(subjects)

        if subjects_found == 0:
            update_progress(100.0, "Context is already empty")
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

        update_progress(
            30.0,
            f"Found {subjects_found} subjects to {'delete' if not dry_run else 'analyze'} (using individual requests)",
        )

        if dry_run:
            update_progress(
                100.0,
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

        update_progress(
            40.0,
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

                # Update progress for deletions (40% to 85%)
                deletion_progress = 40.0 + ((i + 1) / total_futures) * 45.0
                update_progress(
                    deletion_progress,
                    f"Deleted {subjects_deleted} of {subjects_found} subjects (individual requests)",
                )

        update_progress(90.0, "Computing cleanup results")

        # Calculate metrics
        duration = time.time() - start_time
        success_rate = (subjects_deleted / subjects_found * 100) if subjects_found > 0 else 100.0
        performance = subjects_deleted / duration if duration > 0 else 0.0

        # Delete context if requested (not supported by Schema Registry API)
        if delete_context_after and subjects_deleted == subjects_found:
            context_deleted = False  # Context deletion not supported by API
            update_progress(95.0, "Context deletion not supported by API")

        update_progress(
            100.0,
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
    JSON-RPC batching approach for MCP 2025-06-18 compliance.
    """
    try:
        url = registry_client.build_context_url(f"/subjects/{subject}", context)
        response = registry_client.session.delete(url, auth=registry_client.auth, headers=registry_client.headers)
        return response.status_code in [200, 404]  # 404 is OK, subject already deleted
    except Exception:
        return False


@structured_output("clear_multiple_contexts_batch", fallback_on_error=True)
def clear_multiple_contexts_batch_tool(
    contexts: List[str],
    registry_manager,
    registry_mode: str,
    registry: Optional[str] = None,
    delete_contexts_after: bool = True,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Clear multiple contexts in a registry using application-level batch operations.

    ⚠️  APPLICATION-LEVEL BATCHING: This performs application-level batching by
        making individual JSON-RPC requests for each operation. JSON-RPC batching
        has been disabled per MCP 2025-06-18 specification compliance.

    **LONG-DURATION OPERATION** - Uses task queue pattern.
    This operation runs asynchronously and returns a task_id immediately.
    Use get_task_status(task_id) to monitor progress and get results.

    Performance Notes:
    - Uses parallel processing with ThreadPoolExecutor for efficiency
    - Individual requests maintain protocol compliance
    - Client-side request coordination replaces JSON-RPC batching

    Args:
        contexts: List of context names to clear
        registry: Registry name to clear contexts from (uses default if not specified)
        delete_contexts_after: Whether to delete the contexts after clearing subjects
        dry_run: If True, only simulate the operation without making changes

    Returns:
        Task information with task_id for monitoring progress with structured validation
    """
    try:
        # Resolve registry name BEFORE creating task (critical for task lookup)
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

        # Create async task with resolved registry name
        task = task_manager.create_task(
            TaskType.CLEANUP,
            metadata={
                "operation": "clear_multiple_contexts_batch",
                "contexts": contexts,
                "registry": registry,  # Now always a resolved string, never None
                "delete_contexts_after": delete_contexts_after,
                "dry_run": dry_run,
                "batching_type": "application_level",  # For clarity
                "jsonrpc_batching": False,  # Explicitly disabled
            },
        )

        # Start async execution
        try:
            # Check if there's a running event loop
            asyncio.get_running_loop()
            asyncio.create_task(
                task_manager.execute_task(
                    task,
                    _execute_clear_multiple_contexts_batch,
                    contexts=contexts,
                    registry=registry,
                    registry_manager=registry_manager,
                    delete_contexts_after=delete_contexts_after,
                    dry_run=dry_run,
                )
            )
        except RuntimeError:
            # No running event loop, use thread pool to run the task
            def run_task():
                asyncio.run(
                    task_manager.execute_task(
                        task,
                        _execute_clear_multiple_contexts_batch,
                        contexts=contexts,
                        registry=registry,
                        registry_manager=registry_manager,
                        delete_contexts_after=delete_contexts_after,
                        dry_run=dry_run,
                    )
                )

            thread = threading.Thread(target=run_task)
            thread.start()

        # Return structured response
        result = {
            "message": "Multiple contexts cleanup started as async task (application-level batching)",
            "task_id": task.id,
            "task": task.to_dict(),
            "operation_info": {
                "operation": "clear_multiple_contexts_batch",
                "expected_duration": "long",
                "async_pattern": "task_queue",
                "batching_type": "application_level",
                "jsonrpc_batching_disabled": True,
                "guidance": "Long-running operation using individual requests. Returns task_id immediately. Use get_task_status() to monitor progress.",
                "registry_mode": registry_mode,
                "performance_note": "Uses parallel individual requests instead of JSON-RPC batching for MCP 2025-06-18 compliance",
            },
            "operation": "clear_multiple_contexts_batch",
            "dry_run": dry_run,
            "total_items": len(contexts),
            "successful": 0,  # Will be updated by task
            "failed": 0,  # Will be updated by task
            "registry_mode": registry_mode,
            "mcp_protocol_version": "2025-06-18",
        }

        return result

    except Exception as e:
        return create_error_response(str(e), error_code="BATCH_OPERATION_FAILED", registry_mode=registry_mode)


def _execute_clear_multiple_contexts_batch(
    contexts: List[str],
    registry: str,
    registry_manager,
    delete_contexts_after: bool = True,
    dry_run: bool = True,
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
        # Get the current task ID from task manager for progress updates
        current_task = None
        for task in task_manager.list_tasks(status=TaskStatus.RUNNING):
            if (
                task.metadata
                and task.metadata.get("operation") == "clear_multiple_contexts_batch"
                and task.metadata.get("registry") == registry
            ):
                current_task = task
                break

        def update_progress(progress: float, message: str = ""):
            if current_task:
                task_manager.update_progress(current_task.id, progress)
            if message:
                logger.info(f"Multi-Context Clear Progress {progress:.1f}%: {message}")

        # Get registry client (registry is already resolved, never None here)
        registry_client = registry_manager.get_registry(registry)

        update_progress(
            3.0,
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

        update_progress(8.0, "Registry client connected")

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

        update_progress(15.0, "Starting context processing with individual requests")

        # Process each context using individual requests
        total_contexts = len(contexts)
        for i, context in enumerate(contexts, 1):
            try:
                # Get subjects in context
                subjects = registry_client.get_subjects(context)
                if isinstance(subjects, dict) and "error" in subjects:
                    subjects = []
                total_subjects_found += len(subjects)

                context_progress_start = 15.0 + ((i - 1) / total_contexts) * 70.0
                context_progress_end = 15.0 + (i / total_contexts) * 70.0

                update_progress(
                    context_progress_start,
                    f"Processing context {i}/{total_contexts}: '{context}' ({len(subjects)} subjects, individual requests)",
                )

                if dry_run:
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

                update_progress(
                    context_progress_end,
                    f"Completed context '{context}' - deleted {context_deleted_count} subjects using individual requests",
                )

            except Exception as e:
                errors.append(f"Error processing context '{context}': {str(e)}")

        update_progress(90.0, "Computing final results")

        duration = time.time() - start_time
        success_rate = (total_subjects_deleted / total_subjects_found * 100) if total_subjects_found > 0 else 100.0
        subjects_per_second = total_subjects_deleted / duration if duration > 0 else 0.0

        message = (
            f"DRY RUN: Would delete {total_subjects_found} subjects from {len(contexts)} contexts using individual requests"
            if dry_run
            else f"Successfully cleared {len(contexts)} contexts - deleted {total_subjects_deleted}/{total_subjects_found} subjects using individual requests"
        )

        update_progress(100.0, message)

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
