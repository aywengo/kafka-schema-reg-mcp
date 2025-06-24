# Elicitation Capability for Interactive Workflows

The Kafka Schema Registry MCP Server now supports **elicitation capability** per the MCP 2025-06-18 specification, enabling interactive workflows where tools can request missing information from users to guide them through complex operations.

## Overview

Elicitation allows MCP tools to interactively request missing information from users when:
- Schema definitions are incomplete
- Migration preferences are not specified  
- Compatibility issues need resolution
- Context metadata is missing
- Export format preferences are needed

This creates a more intelligent, guided user experience that helps users through complex schema management workflows.

## Key Features

### ✨ Interactive Tools
- **register_schema_interactive**: Guided schema field definition
- **migrate_context_interactive**: Interactive migration configuration
- **check_compatibility_interactive**: Compatibility resolution guidance
- **create_context_interactive**: Context metadata collection
- **export_global_interactive**: Export preference selection

### 🔧 Elicitation Management
- **list_elicitation_requests**: View pending elicitation requests
- **get_elicitation_request**: Get details of specific requests
- **cancel_elicitation_request**: Cancel pending requests
- **get_elicitation_status**: System-wide elicitation status

### 🛡️ Robust Design
- Multi-round conversation support
- Timeout handling with automatic cleanup
- Graceful fallback for non-supporting clients
- Structured validation with JSON Schema
- Full MCP 2025-06-18 protocol compliance

## Elicitation Types

### Text Input
Simple string responses for open-ended questions:
```json
{
  "name": "description",
  "type": "text",
  "label": "Schema Description",
  "placeholder": "Describe what this schema represents",
  "required": false
}
```

### Choice Selection
Multiple choice options for configuration:
```json
{
  "name": "field_type",
  "type": "choice",
  "label": "Field Type",
  "options": ["string", "int", "long", "boolean", "double"],
  "required": true,
  "default": "string"
}
```

### Confirmation
Yes/no decisions for critical operations:
```json
{
  "name": "dry_run",
  "type": "choice",
  "label": "Perform Dry Run First?",
  "options": ["true", "false"],
  "required": true,
  "default": "true"
}
```

### Multi-field Forms
Complex data collection with multiple fields:
```json
{
  "type": "form",
  "title": "Define Schema Field",
  "fields": [
    {
      "name": "field_name",
      "type": "text",
      "required": true,
      "placeholder": "e.g., user_id, email, timestamp"
    },
    {
      "name": "field_type", 
      "type": "choice",
      "options": ["string", "int", "long", "boolean"],
      "required": true,
      "default": "string"
    },
    {
      "name": "nullable",
      "type": "choice",
      "options": ["true", "false"],
      "required": true,
      "default": "false"
    }
  ],
  "allow_multiple": true
}
```

## Usage Examples

### Interactive Schema Registration

When registering a schema without complete field definitions:

```python
# Call the interactive version
result = await register_schema_interactive(
    subject="user-events",
    schema_definition={
        "type": "record",
        "name": "UserEvent", 
        "fields": []  # Empty - will trigger elicitation
    }
)

# The tool will elicit field definitions:
# "What fields should the user-events schema contain?"
# → Field Name: "user_id"
# → Field Type: "string" 
# → Nullable: "false"
# → Documentation: "Unique identifier for the user"

# Result includes elicitation metadata:
# {
#   "success": true,
#   "id": 42,
#   "elicitation_used": true,
#   "elicited_fields": ["field_name", "field_type", "nullable", "documentation"]
# }
```

### Interactive Migration Configuration

When migrating contexts without specifying preferences:

```python
# Migration without preferences triggers elicitation
result = await migrate_context_interactive(
    source_registry="dev-registry",
    target_registry="prod-registry",
    context="user-service",
    # Missing: preserve_ids, dry_run, migrate_all_versions
)

# The tool will elicit migration preferences:
# "Configure migration from dev-registry to prod-registry"
# → Preserve Schema IDs: "true"
# → Migrate All Versions: "false" 
# → Dry Run First: "true"
# → Conflict Resolution: "prompt"

# Result includes applied preferences:
# {
#   "success": true,
#   "elicitation_used": true,
#   "elicited_preferences": {
#     "preserve_ids": true,
#     "dry_run": true,
#     "migrate_all_versions": false
#   }
# }
```

### Interactive Compatibility Resolution

When compatibility issues are detected:

```python
# Compatibility check that finds issues
result = await check_compatibility_interactive(
    subject="user-schema",
    schema_definition=incompatible_schema
)

# The tool will elicit resolution strategy:
# "Schema for subject 'user-schema' has compatibility issues"
# → Resolution Strategy: "modify_schema"
# → New Compatibility Level: "FORWARD"
# → Notes: "Make removed fields optional instead"

# Result includes resolution guidance:
# {
#   "compatible": false,
#   "messages": ["Field 'phone' removed"],
#   "resolution_guidance": {
#     "strategy": "modify_schema",
#     "compatibility_level": "FORWARD", 
#     "notes": "Make removed fields optional instead",
#     "elicitation_used": true
#   }
# }
```

### Interactive Context Creation

When creating contexts without metadata:

```python
# Context creation triggers metadata collection
result = await create_context_interactive(
    context="payment-events"
    # Missing: description, owner, environment, tags
)

# The tool will elicit context metadata:
# "Please provide metadata for the new context 'payment-events'"
# → Description: "Payment processing event schemas"
# → Owner: "payment-team"
# → Environment: "production"
# → Tags: "payments,events,finance"

# Result includes collected metadata:
# {
#   "success": true,
#   "context": "payment-events",
#   "elicitation_used": true,
#   "metadata": {
#     "description": "Payment processing event schemas",
#     "owner": "payment-team",
#     "environment": "production",
#     "tags": ["payments", "events", "finance"]
#   }
# }
```

### Interactive Export Configuration

When exporting without format preferences:

```python
# Export without preferences triggers elicitation
result = await export_global_interactive(
    registry="prod-registry"
    # Missing: format, compression, include_versions
)

# The tool will elicit export preferences:
# "Configure export settings for global_export"
# → Export Format: "yaml"
# → Include Metadata: "true"
# → Version Inclusion: "latest"
# → Compression: "gzip"

# Result includes export preferences:
# {
#   "success": true,
#   "exported": 42,
#   "elicitation_used": true,
#   "export_preferences": {
#     "format": "yaml",
#     "compression": "gzip",
#     "include_metadata": true,
#     "include_versions": "latest"
#   }
# }
```

## Elicitation Management

### List Pending Requests

```python
result = list_elicitation_requests()
# {
#   "pending_requests": [
#     {
#       "id": "req-123",
#       "title": "Define Schema Field",
#       "type": "form",
#       "priority": "medium",
#       "created_at": "2025-06-24T07:30:00Z",
#       "expires_at": "2025-06-24T07:40:00Z",
#       "expired": false
#     }
#   ],
#   "total_pending": 1,
#   "elicitation_supported": true
# }
```

### Get Request Details

```python
result = get_elicitation_request("req-123")
# {
#   "request": {
#     "id": "req-123",
#     "type": "form", 
#     "title": "Define Schema Field",
#     "fields": [...],
#     "context": {...}
#   },
#   "response": null,  # Or response data if completed
#   "status": "pending"  # "pending", "completed", or "expired"
# }
```

### Cancel Request

```python
result = cancel_elicitation_request("req-123")
# {
#   "success": true,
#   "message": "Elicitation request 'req-123' cancelled successfully",
#   "data": {
#     "request_id": "req-123",
#     "cancelled": true
#   }
# }
```

### System Status

```python
result = get_elicitation_status()
# {
#   "elicitation_supported": true,
#   "total_pending_requests": 3,
#   "request_details": [
#     {
#       "id": "req-123",
#       "title": "Define Schema Field",
#       "type": "form",
#       "priority": "medium",
#       "expired": false
#     }
#   ]
# }
```

## Fallback Behavior

The elicitation system provides graceful fallback for non-supporting clients:

### Automatic Defaults
When elicitation is not available, tools automatically apply sensible defaults:
- **Schema fields**: Uses common field types (string, int, boolean)
- **Migration**: Safe settings (preserve_ids=true, dry_run=true)
- **Compatibility**: Conservative resolution (modify_schema)
- **Export**: Standard formats (JSON, latest versions only)

### Fallback Indicators
Responses include metadata indicating fallback was used:
```json
{
  "success": true,
  "elicitation_used": false,
  "fallback_applied": true,
  "default_values": {
    "preserve_ids": true,
    "dry_run": true
  }
}
```

## Configuration

### Timeout Settings
Configure elicitation timeouts for different operations:
```python
# Schema definition: 10 minutes (complex forms)
request.timeout_seconds = 600

# Migration preferences: 5 minutes (multiple choices)  
request.timeout_seconds = 300

# Export preferences: 3 minutes (simple selections)
request.timeout_seconds = 180
```

### Priority Levels
Set elicitation priority for client UI ordering:
```python
# High priority: Critical operations requiring immediate attention
request.priority = ElicitationPriority.HIGH

# Medium priority: Standard workflow guidance  
request.priority = ElicitationPriority.MEDIUM

# Low priority: Optional metadata collection
request.priority = ElicitationPriority.LOW
```

### Client Capability Detection
The system automatically detects client elicitation support:
```python
if is_elicitation_supported():
    # Use full interactive workflows
    response = await elicit_user_input(request)
else:
    # Use fallback defaults
    response = apply_default_values(request)
```

## Best Practices

### 🎯 When to Use Elicitation
- **Missing required information**: Schema fields, migration settings
- **Complex configuration**: Multi-step workflows with dependencies
- **Error resolution**: Compatibility issues, validation failures  
- **Optional enhancement**: Metadata collection, preference tuning

### ⚡ Performance Considerations
- **Batch operations**: Group related elicitations together
- **Timeout management**: Set appropriate timeouts for complexity
- **Fallback readiness**: Always provide sensible defaults
- **Async handling**: Use non-blocking elicitation patterns

### 🛡️ Error Handling
- **Validation**: Always validate elicited responses
- **Timeout recovery**: Handle timeout gracefully with defaults
- **Cancellation**: Allow users to cancel long-running elicitations
- **Retry logic**: Support re-elicitation for invalid responses

### 📋 User Experience
- **Clear titles**: Use descriptive elicitation titles
- **Helpful descriptions**: Explain what information is needed
- **Smart defaults**: Pre-populate common values
- **Progressive disclosure**: Break complex forms into steps

## Integration with MCP Clients

### Claude Desktop
Claude Desktop fully supports the elicitation capability with rich form UI:
- Interactive form widgets for complex elicitations
- Progress indicators for multi-step workflows
- Validation feedback for invalid responses
- Timeout warnings and extension options

### Other MCP Clients
The implementation provides graceful degradation for clients without elicitation support:
- Automatic fallback to sensible defaults
- Clear indicators when fallback is used
- Documentation for enabling elicitation support
- Migration guides for client developers

## Migration Guide

### Existing Tool Compatibility
All existing tools remain fully functional:
```python
# Original tools work unchanged
result = register_schema(subject, complete_schema)

# Interactive variants provide additional guidance
result = register_schema_interactive(subject, incomplete_schema)
```

### Gradual Adoption
Adopt elicitation incrementally:
1. **Start with high-value scenarios**: Schema registration, migration
2. **Add management tools**: Monitor elicitation usage and performance
3. **Expand coverage**: Add elicitation to more complex workflows
4. **Optimize experience**: Tune timeouts, defaults, and validation

### Client Updates
Update MCP clients to support elicitation:
1. **Implement elicitation protocol**: Handle elicitation requests/responses
2. **Build UI components**: Forms, choice selectors, progress indicators
3. **Add timeout handling**: Graceful timeout with user options
4. **Test fallback**: Ensure graceful degradation when elicitation fails

## Troubleshooting

### Common Issues

**Elicitation requests timing out**
- Check client elicitation support
- Increase timeout for complex forms
- Verify network connectivity
- Review client logs for errors

**Invalid responses rejected**
- Check field validation rules
- Verify required fields are provided
- Validate choice options match exactly
- Review field type requirements

**Fallback always triggered**
- Verify client declares elicitation capability
- Check MCP protocol version compatibility
- Review client elicitation implementation
- Test with known-working clients

### Debug Information

Enable debug logging to troubleshoot elicitation issues:
```python
# Set logging level for elicitation module
logging.getLogger('elicitation').setLevel(logging.DEBUG)

# Check elicitation status
status = get_elicitation_status()
print(f"Elicitation supported: {status['elicitation_supported']}")
print(f"Pending requests: {status['total_pending_requests']}")
```

### Performance Monitoring

Monitor elicitation performance:
```python
# List all elicitation requests with timing
requests = list_elicitation_requests()
for req in requests['pending_requests']:
    duration = datetime.now() - datetime.fromisoformat(req['created_at'])
    print(f"Request {req['id']}: {duration.total_seconds()}s")
```

## Security Considerations

### Input Validation
All elicited responses are validated:
- Required field enforcement
- Type checking (email, choice options)
- Length limits and pattern matching  
- Sanitization of user inputs

### Timeout Protection
Prevents resource exhaustion:
- Automatic cleanup of expired requests
- Configurable timeout limits
- Memory management for pending requests
- Background cleanup tasks

### Access Control
Elicitation respects existing OAuth scopes:
- `read` scope: View elicitation status
- `write` scope: Submit elicitation responses  
- `admin` scope: Cancel elicitation requests
- Tool-specific scope requirements maintained

---

## Conclusion

The elicitation capability transforms the Kafka Schema Registry MCP Server from a command-driven interface into an intelligent, interactive assistant that guides users through complex schema management workflows. By implementing the MCP 2025-06-18 elicitation specification, the server can now:

- **Guide users** through complex schema registration with field-by-field assistance
- **Collect preferences** for migration and export operations interactively
- **Resolve conflicts** by eliciting user preferences for compatibility issues
- **Enhance metadata** by collecting organizational context for schemas and contexts
- **Maintain compatibility** through graceful fallback for non-supporting clients

This creates a more intuitive, error-resistant, and user-friendly experience while preserving all existing functionality and maintaining full backward compatibility.
