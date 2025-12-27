#!/usr/bin/env python3
"""
Enhanced Batch Operations Module with Context Integration

This module demonstrates how to integrate the enhanced task management
with MCP Context for better progress reporting in long-running operations.

This is an example implementation showing how to modify existing batch
operations to leverage MCP's progress reporting and logging capabilities.
"""

import asyncio
import time
from typing import TYPE_CHECKING, Any, Dict, Optional

from schema_validation import create_error_response, structured_output
from task_management_enhanced import ProgressReporter, TaskType, create_context_aware_task, enhanced_task_manager

if TYPE_CHECKING:
    from fastmcp.server.context import Context


@structured_output("clear_context_batch_enhanced", fallback_on_error=True)
async def clear_context_batch_enhanced_tool(
    context: str,
    registry_manager,
    registry_mode: str,
    ctx: Optional["Context"] = None,  # MCP Context injected by FastMCP
    registry: Optional[str] = None,
    delete_context_after: bool = True,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """
    Enhanced version of clear_context_batch with MCP Context integration.

    This version demonstrates:
    1. Automatic context injection from FastMCP
    2. Progress reporting through MCP protocol
    3. Structured logging via context
    4. Better async/await patterns

    Args:
        context: The context to clear
        ctx: MCP Context (automatically injected by FastMCP when available)
        registry: The registry to operate on
        delete_context_after: Whether to delete the context after clearing
        dry_run: If True, only simulate the operation

    Returns:
        Task information with enhanced monitoring capabilities
    """
    try:
        # Log operation start if context available
        if ctx:
            await ctx.info(f"Starting batch clear operation for context '{context}'", logger_name="BatchOperations")

        # Resolve registry
        if registry is None:
            available_registries = registry_manager.list_registries()
            if available_registries:
                registry = available_registries[0]
            else:
                return create_error_response(
                    "No registries available",
                    error_code="NO_REGISTRIES_AVAILABLE",
                    registry_mode=registry_mode,
                )

        # Validate registry
        registry_client = registry_manager.get_registry(registry)
        if not registry_client:
            if ctx:
                await ctx.error(f"Registry '{registry}' not found", logger_name="BatchOperations")
            return create_error_response(
                f"Registry '{registry}' not found",
                error_code="REGISTRY_NOT_FOUND",
                registry_mode=registry_mode,
            )

        # Create task with context
        task = create_context_aware_task(
            TaskType.CLEANUP,
            metadata={
                "operation": "clear_context_batch_enhanced",
                "context": context,
                "registry": registry,
                "delete_context_after": delete_context_after,
                "dry_run": dry_run,
            },
            context=ctx,  # Pass the MCP context
        )

        # Start async execution
        asyncio.create_task(
            enhanced_task_manager.execute_task(
                task,
                _execute_clear_context_enhanced,
                context=context,
                registry=registry,
                registry_manager=registry_manager,
                delete_context_after=delete_context_after,
                dry_run=dry_run,
            )
        )

        result = {
            "message": "Enhanced context cleanup started with progress tracking",
            "task_id": task.id,
            "task": task.to_dict(),
            "features": {
                "progress_reporting": bool(ctx),
                "structured_logging": bool(ctx),
                "context_aware": True,
            },
            "operation_info": {
                "operation": "clear_context_batch_enhanced",
                "expected_duration": "medium",
                "async_pattern": "task_queue",
                "guidance": "Monitor progress via MCP progress notifications or get_task_status()",
            },
            "registry_mode": registry_mode,
            "mcp_protocol_version": "2025-11-25",
        }

        return result

    except Exception as e:
        if ctx:
            await ctx.error(f"Failed to start batch operation: {str(e)}", logger_name="BatchOperations")
        return create_error_response(str(e), error_code="BATCH_OPERATION_FAILED", registry_mode=registry_mode)


async def _execute_clear_context_enhanced(
    context: str,
    registry: str,
    registry_manager,
    delete_context_after: bool = True,
    dry_run: bool = True,
    ctx: Optional["Context"] = None,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Enhanced execution with progress reporting and logging.

    This implementation shows how to:
    1. Use ProgressReporter for structured progress updates
    2. Log detailed information through MCP context
    3. Handle errors with context-aware logging
    """
    start_time = time.time()
    reporter = ProgressReporter(task_id, ctx) if task_id else None

    try:
        # Phase 1: Get subjects (10% of total progress)
        if reporter:
            await reporter.update(0.0, "Fetching subjects from context")

        registry_client = registry_manager.get_registry(registry)
        subjects = registry_client.get_subjects(context)

        if isinstance(subjects, dict) and "error" in subjects:
            raise Exception(f"Failed to get subjects: {subjects.get('error')}")

        subjects_found = len(subjects)

        if ctx:
            await ctx.info(f"Found {subjects_found} subjects in context '{context}'", logger_name="BatchOperations")

        if reporter:
            await reporter.update(10.0, f"Found {subjects_found} subjects")

        if dry_run:
            # Dry run - just report what would be done
            if reporter:
                await reporter.update(100.0, "Dry run completed")
            return {
                "dry_run": True,
                "subjects_found": subjects_found,
                "subjects_to_delete": subjects_found,
                "context_to_delete": delete_context_after,
                "duration": time.time() - start_time,
            }

        # Phase 2: Delete subjects (10% to 90% of progress)
        subjects_deleted = 0
        errors = []

        if subjects_found > 0:
            if reporter:
                async with reporter.phase("Deleting subjects", subjects_found) as phase:
                    for i, subject in enumerate(subjects):
                        try:
                            # Delete subject
                            result = registry_client.delete_subject(subject, context, permanent=False)

                            if isinstance(result, dict) and "error" in result:
                                errors.append({"subject": subject, "error": result.get("error")})
                                if ctx:
                                    await ctx.warning(
                                        f"Failed to delete subject '{subject}': {result.get('error')}",
                                        logger_name="BatchOperations",
                                    )
                            else:
                                subjects_deleted += 1

                            # Update progress
                            await phase.update_item(i)

                        except Exception as e:
                            errors.append({"subject": subject, "error": str(e)})
                            if ctx:
                                await ctx.error(
                                    f"Exception deleting subject '{subject}': {str(e)}", logger_name="BatchOperations"
                                )
        else:
            if reporter:
                await reporter.update(90.0, "No subjects to delete")

        # Phase 3: Delete context if requested (90% to 100%)
        context_deleted = False
        if delete_context_after and subjects_deleted == subjects_found:
            if reporter:
                await reporter.update(90.0, "Deleting context")

            try:
                result = registry_client.delete_context(context)
                if isinstance(result, dict) and "error" in result:
                    if ctx:
                        await ctx.warning(
                            f"Failed to delete context: {result.get('error')}", logger_name="BatchOperations"
                        )
                else:
                    context_deleted = True
                    if ctx:
                        await ctx.info(f"Successfully deleted context '{context}'", logger_name="BatchOperations")
            except Exception as e:
                if ctx:
                    await ctx.error(f"Exception deleting context: {str(e)}", logger_name="BatchOperations")

        if reporter:
            await reporter.update(100.0, "Operation completed")

        # Final summary
        duration = time.time() - start_time
        if ctx:
            await ctx.info(
                f"Batch operation completed: {subjects_deleted}/{subjects_found} subjects deleted"
                + (f", context {'deleted' if context_deleted else 'retained'}" if delete_context_after else "")
                + f" in {duration:.2f}s",
                logger_name="BatchOperations",
            )

        return {
            "dry_run": False,
            "subjects_found": subjects_found,
            "subjects_deleted": subjects_deleted,
            "context_deleted": context_deleted,
            "errors": errors,
            "duration": duration,
        }

    except Exception as e:
        if ctx:
            await ctx.error(f"Batch operation failed: {str(e)}", logger_name="BatchOperations")
        raise


# Example of a simpler operation with basic progress reporting
@structured_output("count_schemas_enhanced", fallback_on_error=True)
async def count_schemas_with_progress_tool(
    registry_manager,
    registry_mode: str,
    ctx: Optional["Context"] = None,
    registry: Optional[str] = None,
    include_all_contexts: bool = False,
) -> Dict[str, Any]:
    """
    Count schemas with progress reporting for each context.

    This simpler example shows how even quick operations can benefit
    from progress reporting when they involve multiple steps.
    """
    try:
        if ctx:
            await ctx.debug("Starting schema count operation", logger_name="Statistics")

        # Get client
        if registry_mode == "single":
            from schema_registry_common import get_default_client

            client = get_default_client(registry_manager)
        else:
            client = registry_manager.get_registry(registry)

        if client is None:
            return create_error_response(
                f"Registry '{registry}' not found or not configured",
                error_code="REGISTRY_NOT_FOUND",
                registry_mode=registry_mode,
            )

        total_schemas = 0
        context_counts = []

        if include_all_contexts:
            # Get all contexts
            contexts = client.get_contexts()
            if isinstance(contexts, dict) and "error" in contexts:
                raise Exception(f"Failed to get contexts: {contexts.get('error')}")

            # Count schemas in each context with progress
            for i, context_name in enumerate(contexts):
                if ctx:
                    # Report progress based on context processing
                    progress = (i / len(contexts)) * 100.0
                    await ctx.report_progress(progress, 100.0, f"Counting schemas in context '{context_name}'")

                subjects = client.get_subjects(context_name)
                if not isinstance(subjects, dict):
                    count = len(subjects)
                    total_schemas += count
                    context_counts.append({"context": context_name, "count": count})

            # Final progress
            if ctx:
                await ctx.report_progress(100.0, 100.0, "Count completed")

        else:
            # Just count default context
            subjects = client.get_subjects()
            if not isinstance(subjects, dict):
                total_schemas = len(subjects)

        return {
            "registry": registry or "default",
            "total_schemas": total_schemas,
            "context_counts": context_counts if include_all_contexts else None,
            "registry_mode": registry_mode,
        }

    except Exception as e:
        if ctx:
            await ctx.error(f"Schema count failed: {str(e)}", logger_name="Statistics")
        return create_error_response(str(e), error_code="SCHEMA_COUNT_FAILED", registry_mode=registry_mode)
