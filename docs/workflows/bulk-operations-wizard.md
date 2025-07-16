# Bulk Operations Wizard

The Bulk Operations Wizard provides an interactive, safe way to perform administrative tasks across multiple schemas or contexts in your Kafka Schema Registry. Using elicitation-based workflows, it ensures operations are executed safely with proper confirmations and rollback capabilities.

## Overview

The Bulk Operations Wizard supports four main operation types:

1. **Schema Updates** - Modify compatibility settings, naming conventions, or metadata across multiple schemas
2. **Migrations** - Move schemas between contexts or registries
3. **Cleanup** - Remove deprecated schemas, clean up test schemas, or purge old versions
4. **Configuration** - Apply security policies, retention policies, or access controls

## Key Features

### Safety First
- **Mandatory Dry-Run**: All destructive operations require a dry-run preview
- **Automatic Backups**: Creates backups before making changes
- **Rollback Support**: Automatic rollback on errors
- **Consumer Impact Analysis**: Checks for active consumers before destructive operations
- **Progress Monitoring**: Real-time progress tracking with abort capability

### Interactive Workflows
- **Elicitation-Based**: Guides users through complex operations step-by-step
- **Pattern Matching**: Support for wildcard patterns (e.g., `test-*`, `deprecated-*`)
- **Preview Generation**: Shows exactly what will be changed before execution
- **Confirmation Steps**: Multiple confirmation points for destructive operations

## Usage Examples

### Starting the Wizard

```python
# Start the wizard without pre-selecting operation type
result = await wizard.start_wizard()

# Or start with a specific operation type
result = await wizard.start_wizard(BulkOperationType.CLEANUP)
```

### Example: Bulk Schema Update

Update compatibility settings for all test schemas:

```python
# The wizard will guide you through:
# 1. Selecting schemas (with pattern support)
# 2. Choosing update type (compatibility/naming/metadata)
# 3. Setting new values
# 4. Reviewing preview
# 5. Confirming operation

result = await wizard.start_wizard(BulkOperationType.SCHEMA_UPDATE)
```

#### Elicitation Flow Example:

```
1. "Select schemas to update"
   Options: 
   - Individual schemas
   - test-* (All test schemas)
   - deprecated-* (All deprecated schemas)
   - * (All schemas)

2. "What would you like to update?"
   - Compatibility Settings
   - Naming Conventions
   - Schema Metadata

3. "Select new compatibility level"
   - BACKWARD
   - FORWARD
   - FULL
   - NONE

4. Preview: "This operation will affect 47 schemas. View details?"
   Shows affected schemas, estimated duration, warnings

5. "Do you want to proceed with this operation?"
   Requires explicit confirmation
```

### Example: Bulk Cleanup

Clean up deprecated schemas with consumer safety:

```python
result = await wizard.start_wizard(BulkOperationType.CLEANUP)
```

#### Elicitation Flow:

```
1. "What type of cleanup?"
   - Deprecated schemas
   - Test schemas
   - Old versions
   - Custom pattern

2. "Select schemas to clean up"
   Shows matching schemas based on cleanup type

3. "Cleanup options"
   - Create backup: Yes/No
   - Permanent delete: Yes/No
   - Version retention: Keep last N versions

4. Consumer Impact Check
   "Active consumers detected (3 consumers). How should we proceed?"
   - Wait for consumers to catch up
   - Force operation (may disrupt consumers)
   - Skip schemas with active consumers
   - Cancel operation

5. Final confirmation with warnings
```

### Example: Bulk Migration

Migrate schemas between contexts or registries:

```python
result = await wizard.start_wizard(BulkOperationType.MIGRATION)
```

#### Configuration Options:

```python
config = BulkOperationConfig(
    operation_type=BulkOperationType.MIGRATION,
    dry_run=True,
    batch_size=20,
    delay_between_batches=2.0,
    create_backup=True,
    rollback_on_error=True
)
```

## Operation Types Detail

### Schema Updates

Supported update types:
- **Compatibility Settings**: Change BACKWARD, FORWARD, FULL, or NONE compatibility
- **Naming Conventions**: Apply consistent naming patterns
- **Metadata Updates**: Add or update schema metadata in bulk

### Migrations

Supported migration types:
- **Context Migration**: Move schemas between contexts within a registry
- **Cross-Registry Migration**: Copy schemas to a different registry
- **Version Archival**: Archive old schema versions to backup location

### Cleanup Operations

Supported cleanup types:
- **Deprecated Schema Removal**: Remove schemas marked as deprecated
- **Test Schema Cleanup**: Remove temporary test schemas
- **Version Purging**: Remove old versions keeping only recent ones
- **Pattern-Based Cleanup**: Remove schemas matching custom patterns

### Configuration Changes

Supported configuration types:
- **Security Policies**: Apply access controls and permissions
- **Retention Policies**: Set how long to keep schema versions
- **Mode Settings**: Change registry or subject modes
- **Compliance Settings**: Apply organizational compliance rules

## Advanced Features

### Batch Processing

Operations are processed in configurable batches:

```python
# Configure batch processing
config = BulkOperationConfig(
    batch_size=50,  # Process 50 items at a time
    delay_between_batches=2.0  # 2 second delay between batches
)
```

### Progress Tracking

Monitor long-running operations:

```python
# The wizard returns a task_id for tracking
result = await wizard.start_wizard()
task_id = result['task_id']

# Check progress
status = await task_manager.get_task_status(task_id)
print(f"Progress: {status['processed']}/{status['total_items']}")
```

### Dry Run Mode

Test operations without making changes:

```python
config = BulkOperationConfig(
    dry_run=True  # Preview changes without executing
)
```

### Custom Callbacks

Add custom progress callbacks:

```python
def progress_callback(processed, total, message):
    print(f"Progress: {processed}/{total} - {message}")

config = BulkOperationConfig(
    progress_callback=progress_callback
)
```

## Safety Considerations

### Destructive Operations

The wizard implements multiple safety layers for destructive operations:

1. **Preview Required**: Always shows what will be affected
2. **Consumer Check**: Analyzes active consumer impact
3. **Backup Creation**: Automatic backup before changes
4. **Rollback Ready**: Can undo changes if errors occur
5. **Explicit Confirmation**: Requires typing "YES" for destructive ops

### Error Handling

The wizard handles errors gracefully:

```python
try:
    result = await wizard.start_wizard()
    if result['status'] == 'success':
        print(f"Processed {result['processed']} items")
    else:
        print(f"Operation failed: {result['error']}")
except Exception as e:
    print(f"Wizard error: {e}")
```

## Best Practices

1. **Always Review Previews**: Take time to review the preview before confirming
2. **Use Patterns Carefully**: Test patterns with dry-run first
3. **Monitor Progress**: For large operations, monitor the task progress
4. **Keep Backups**: Even with automatic backups, maintain your own
5. **Check Consumers**: Always verify consumer impact for production schemas
6. **Start Small**: Test operations on a small subset first

## Integration with MCP Tools

The Bulk Operations Wizard integrates with other MCP tools:

```python
# Use with elicitation for custom workflows
elicitation_request = {
    "operation": "bulk_cleanup",
    "context": "production",
    "pattern": "deprecated-*"
}

# Use with task management for monitoring
task_status = await get_task_status(task_id)

# Use with migration tools for complex migrations
migration_result = await migrate_with_wizard(
    source_registry="prod",
    target_registry="backup"
)
```

## Troubleshooting

### Common Issues

1. **Operation Timeout**
   - Reduce batch size
   - Increase delay between batches
   - Check registry performance

2. **Consumer Impact Detected**
   - Wait for consumers to catch up
   - Schedule during maintenance window
   - Use skip option for affected schemas

3. **Rollback Failed**
   - Check backup integrity
   - Verify registry permissions
   - Contact admin for manual intervention

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger('BulkOperationsWizard').setLevel(logging.DEBUG)
```

## Future Enhancements

Planned improvements:
- Scheduled operations support
- Operation templates for common tasks
- Audit trail integration
- Performance optimizations for large batches
- Custom operation plugins

## Related Documentation

- [Elicitation Framework](./elicitation-framework.md)
- [Task Management](./task-management.md)
- [Migration Tools](./migration-guide.md)
- [Schema Registry Best Practices](../best-practices/schema-management.md)
