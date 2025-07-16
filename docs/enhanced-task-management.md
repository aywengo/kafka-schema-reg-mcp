# Enhanced Long-Running Task Support for Python MCP SDK

## Overview

This enhancement improves the Python MCP SDK's handling of long-running tasks by integrating the existing task management system with MCP's Context object for better progress reporting and logging capabilities.

## Key Improvements

### 1. **Context-Aware Task Management**

The enhanced task manager (`task_management_enhanced.py`) automatically integrates with MCP's Context object to provide:

- **Automatic Progress Reporting**: Tasks can report progress through the MCP protocol's progress notification system
- **Structured Logging**: All task lifecycle events are logged through the MCP context
- **Progress Token Support**: Automatically extracts and uses progress tokens from MCP requests

### 2. **Enhanced Progress Reporting**

The new `ProgressReporter` class provides a clean API for reporting progress from within task functions:

```python
async def my_task_function(data, context: Context, task_id: str):
    reporter = ProgressReporter(task_id, context)
    
    # Simple progress update
    await reporter.update(25.0, "Processing first batch")
    
    # Phase-based progress with automatic calculation
    async with reporter.phase("Processing items", total=100) as phase:
        for i, item in enumerate(items):
            # Process item...
            await phase.update_item(i)
```

### 3. **Automatic Context Injection**

Tool functions can now receive the MCP Context automatically:

```python
@server.tool
async def my_long_running_tool(
    data: str,
    ctx: Context  # Automatically injected by FastMCP
) -> dict:
    # Create a context-aware task
    task = create_context_aware_task(
        TaskType.EXPORT,
        metadata={"data": data},
        context=ctx
    )
    
    # Start async execution with context
    asyncio.create_task(
        enhanced_task_manager.execute_task(
            task,
            process_data,
            data=data
        )
    )
    
    return {"task_id": task.id}
```

### 4. **Lifecycle Logging**

All task events are automatically logged through the MCP context:

- Task creation
- Task start
- Progress milestones (25%, 50%, 75%)
- Task completion/failure/cancellation

## Implementation Examples

### Example 1: Enhanced Batch Operation

The `batch_operations_enhanced.py` file demonstrates how to enhance existing batch operations:

```python
@structured_output("clear_context_batch_enhanced", fallback_on_error=True)
async def clear_context_batch_enhanced_tool(
    context: str,
    registry_manager,
    registry_mode: str,
    ctx: Optional[Context] = None,  # MCP Context
    registry: Optional[str] = None,
    delete_context_after: bool = True,
    dry_run: bool = True,
) -> Dict[str, Any]:
    # Log operation start
    if ctx:
        await ctx.info(
            f"Starting batch clear operation for context '{context}'",
            logger_name="BatchOperations"
        )
    
    # Create task with context
    task = create_context_aware_task(
        TaskType.CLEANUP,
        metadata={...},
        context=ctx
    )
    
    # Execute with context integration
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
```

### Example 2: Progress Phases

The execution function shows how to use progress phases:

```python
async def _execute_clear_context_enhanced(
    context: str,
    registry: str,
    registry_manager,
    delete_context_after: bool = True,
    dry_run: bool = True,
    ctx: Optional[Context] = None,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    reporter = ProgressReporter(task_id, ctx)
    
    # Phase 1: Setup (0-10%)
    await reporter.update(0.0, "Fetching subjects from context")
    subjects = registry_client.get_subjects(context)
    await reporter.update(10.0, f"Found {len(subjects)} subjects")
    
    # Phase 2: Main processing (10-90%)
    async with reporter.phase("Deleting subjects", len(subjects)) as phase:
        for i, subject in enumerate(subjects):
            # Delete subject...
            await phase.update_item(i)
    
    # Phase 3: Cleanup (90-100%)
    await reporter.update(90.0, "Deleting context")
    # Delete context...
    await reporter.update(100.0, "Operation completed")
```

### Example 3: Simple Operations with Progress

Even simple operations can benefit from progress reporting:

```python
@structured_output("count_schemas_enhanced", fallback_on_error=True)
async def count_schemas_with_progress_tool(
    registry_manager,
    registry_mode: str,
    ctx: Optional[Context] = None,
    include_all_contexts: bool = False,
) -> Dict[str, Any]:
    if ctx:
        await ctx.debug("Starting schema count operation", logger_name="Statistics")
    
    contexts = client.get_contexts()
    
    for i, context_name in enumerate(contexts):
        if ctx:
            progress = (i / len(contexts)) * 100.0
            await ctx.report_progress(
                progress,
                100.0,
                f"Counting schemas in context '{context_name}'"
            )
        
        # Count schemas...
    
    if ctx:
        await ctx.report_progress(100.0, 100.0, "Count completed")
```

## Migration Guide

To migrate existing tools to use the enhanced task management:

1. **Add Context Parameter**: Add `ctx: Optional[Context] = None` to tool function parameters
2. **Replace Task Creation**: Use `create_context_aware_task()` instead of `task_manager.create_task()`
3. **Update Execution Functions**: Add `ctx` and `task_id` parameters to execution functions
4. **Add Progress Reporting**: Use `ProgressReporter` for structured progress updates
5. **Add Logging**: Use context logging methods (`ctx.info()`, `ctx.debug()`, etc.) instead of logger

## Best Practices

1. **Always Check for Context**: Context may be None in some environments
2. **Use Progress Phases**: For operations with clear stages, use the phase context manager
3. **Report Meaningful Progress**: Include descriptive messages with progress updates
4. **Log Important Events**: Use appropriate log levels for different events
5. **Handle Errors Gracefully**: Always log errors through context when available

## Backward Compatibility

The enhanced task management maintains full backward compatibility:

- The original `task_manager` is aliased to `enhanced_task_manager`
- Existing code without context support continues to work
- Context features are only activated when a context is provided

## Performance Considerations

- Progress updates are throttled to >1% changes to avoid excessive notifications
- Logging is asynchronous and non-blocking
- Context operations fail gracefully if the context is unavailable

## Future Enhancements

Potential future improvements could include:

1. **Automatic Progress Calculation**: Based on operation metadata
2. **Progress Persistence**: Save progress across server restarts
3. **Task Dependencies**: Support for task chains and dependencies
4. **Resource Usage Tracking**: Monitor CPU/memory usage during tasks
5. **Custom Progress Reporters**: Pluggable progress reporting strategies
