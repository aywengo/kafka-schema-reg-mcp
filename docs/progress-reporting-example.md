# Progress Reporting Example: compare_contexts_across_registries

This document demonstrates how the `compare_contexts_across_registries` tool now supports progress reporting through the MCP Context parameter.

## Overview

The `compare_contexts_across_registries` tool has been enhanced to provide real-time progress updates and logging when used with the MCP Context parameter. This allows users to monitor the progress of context comparisons, especially useful for large registries with many subjects.

## Key Features

- **Real-time Progress Updates**: Progress is reported from 0% to 100% with meaningful messages
- **Structured Logging**: Info, debug, and error messages are logged through the MCP context
- **Detailed Progress Phases**: The operation is broken down into logical phases with specific progress ranges
- **Backward Compatible**: The tool works with or without the Context parameter

## Progress Phases

The tool reports progress through these phases:

1. **Initialization (0-10%)**: Setting up registry clients and validating parameters
2. **Source Context Fetching (10-30%)**: Retrieving subjects from the source registry context
3. **Target Context Fetching (30-50%)**: Retrieving subjects from the target registry context
4. **Comparison Building (50-60%)**: Building the comparison data structure
5. **Schema Analysis (60-90%)**: Comparing schema versions for common subjects
6. **Summary & Links (90-100%)**: Building summary and adding resource links

## Usage Example

```python
@mcp.tool()
async def compare_contexts_across_registries(
    source_registry: str,
    target_registry: str,
    source_context: str,
    target_context: str = None,
    *,
    context: Context  # MCP Context automatically injected
):
    """Compare contexts across two registries with progress reporting."""
    return await compare_contexts_across_registries_tool(
        source_registry,
        target_registry,
        source_context,
        registry_manager,
        REGISTRY_MODE,
        target_context,
        context,  # Pass the context for progress reporting
    )
```

## Sample Output

When using the tool with progress reporting enabled:

```
ℹ️  [INFO] Starting context comparison: dev/customer-context vs prod/customer-context
📊 Progress: 0.0% - Initializing context comparison
📊 Progress: 10.0% - Registry clients initialized
ℹ️  [INFO] Fetching subjects from source context: dev/customer-context
📊 Progress: 15.0% - Fetching subjects from dev/customer-context
📊 Progress: 25.0% - Found 3 subjects in source context
ℹ️  [INFO] Fetching subjects from target context: prod/customer-context
📊 Progress: 35.0% - Fetching subjects from prod/customer-context
📊 Progress: 45.0% - Found 2 subjects in target context
📊 Progress: 50.0% - Building comparison structure
📊 Progress: 60.0% - Analyzing subject differences
ℹ️  [INFO] Comparing schemas for 2 common subjects
📊 Progress: 65.0% - Comparing schemas for 2 common subjects
📊 Progress: 65.0% - Comparing schema versions for order-events
📊 Progress: 75.0% - Comparing schema versions for user-events
📊 Progress: 85.0% - Found 0 subjects with version differences
📊 Progress: 90.0% - Building comparison summary
📊 Progress: 95.0% - Adding resource links
ℹ️  [INFO] Context comparison completed successfully
📊 Progress: 100.0% - Context comparison completed
```

## Implementation Details

### Context Parameter

The tool now accepts an optional `Context` parameter:

```python
async def compare_contexts_across_registries_tool(
    source_registry: str,
    target_registry: str,
    source_context: str,
    registry_manager,
    registry_mode: str,
    target_context: Optional[str] = None,
    context: Optional["Context"] = None,  # New parameter for progress reporting
) -> Dict[str, Any]:
```

### Progress Reporting

Progress is reported using the MCP Context methods:

```python
# Report progress with percentage and message
await context.report_progress(25.0, 100.0, "Found 3 subjects in source context")

# Log informational messages
await context.info("Starting context comparison: dev/customer-context vs prod/customer-context")

# Log errors
await context.error("Context comparison failed: Connection timeout")
```

### Conditional Progress Reporting

The tool gracefully handles cases where no context is provided:

```python
# Only report progress if context is available
if context:
    await context.report_progress(50.0, 100.0, "Building comparison structure")
```

## Benefits

1. **Better User Experience**: Users can see real-time progress instead of waiting for completion
2. **Debugging Support**: Detailed logging helps identify issues during comparison
3. **Large Registry Support**: Essential for comparing contexts with hundreds of subjects
4. **Monitoring Integration**: Progress can be monitored by external systems
5. **Backward Compatibility**: Existing code continues to work without changes

## Best Practices

1. **Always Check for Context**: Use `if context:` before calling context methods
2. **Meaningful Messages**: Provide descriptive progress messages
3. **Logical Phases**: Break operations into logical phases with appropriate progress ranges
4. **Error Handling**: Always log errors through the context when available
5. **Completion Logging**: Log successful completion with final progress update

## Testing

The implementation includes comprehensive testing with mock objects to verify:

- Progress reporting works correctly
- Logging messages are generated
- The tool works with and without context
- Error handling includes context logging

Run the test with:

```bash
python test_progress_reporting.py
```

This enhancement makes the `compare_contexts_across_registries` tool much more user-friendly and suitable for production environments where monitoring long-running operations is essential. 