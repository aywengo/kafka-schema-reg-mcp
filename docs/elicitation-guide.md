# Elicitation Capability User Guide

## Overview

The Kafka Schema Registry MCP Server now supports **interactive workflows** through the MCP 2025-06-18 elicitation capability. This allows tools to interactively request missing information from users, enabling guided schema operations and intelligent workflow assistance.

## 🎯 Key Features

- **Interactive Schema Registration** - Guided field definition with validation
- **Migration Preference Collection** - Smart migration configuration
- **Compatibility Resolution** - Automated conflict resolution guidance  
- **Context Metadata Elicitation** - Organizational information collection
- **Export Format Selection** - Intelligent export configuration
- **Multi-round Conversations** - Complex workflows with multiple steps
- **Graceful Fallbacks** - Works with all MCP clients (fallback to defaults)

## 🚀 Getting Started

### Enable Elicitation Support

Elicitation is automatically enabled and works with any MCP client. The server will:
1. **Auto-detect** if your client supports elicitation
2. **Use interactive workflows** when supported
3. **Fall back gracefully** to sensible defaults when not supported

No configuration required!

### Interactive Tools Available

| Tool | Purpose | Elicits |
|------|---------|---------|
| `register_schema_interactive` | Schema registration | Field definitions, types, constraints |
| `migrate_context_interactive` | Context migration | Migration preferences, conflict resolution |
| `check_compatibility_interactive` | Schema compatibility | Resolution strategies, compatibility levels |
| `create_context_interactive` | Context creation | Metadata, ownership, environment info |
| `export_global_interactive` | Schema export | Export formats, compression, version selection |

## 📋 Usage Examples

### 1. Interactive Schema Registration

Register a schema with guided field definition:

```python
# Call the interactive tool
result = await mcp.call_tool("register_schema_interactive", {
    "subject": "user-events",
    "schema_type": "AVRO"
    # schema_definition is optional - will be elicited if missing
})
```

**What happens:**
1. Server detects missing field definitions
2. Prompts you for each field: name, type, nullable, defaults, documentation
3. Builds complete schema from your responses
4. Registers the schema successfully

**Elicitation prompts:**
- Field Name: `user_id`, `email`, `timestamp`
- Field Type: `string`, `int`, `long`, `boolean`, etc.
- Nullable: `true` or `false`
- Default Value: (optional)
- Documentation: Field description

### 2. Interactive Migration Configuration

Migrate contexts with intelligent preference collection:

```python
result = await mcp.call_tool("migrate_context_interactive", {
    "source_registry": "staging", 
    "target_registry": "production"
    # Migration preferences will be elicited
})
```

**Elicitation prompts:**
- **Preserve Schema IDs**: Maintain original schema IDs during migration
- **Migrate All Versions**: Include all schema versions or just latest
- **Conflict Resolution**: `skip`, `overwrite`, `merge`, or `prompt`
- **Batch Size**: Number of schemas per batch (1-100)
- **Dry Run**: Preview changes before applying

### 3. Interactive Compatibility Resolution

Get guidance when schemas are incompatible:

```python
result = await mcp.call_tool("check_compatibility_interactive", {
    "subject": "user-profile",
    "schema_definition": {"type": "record", "fields": [...]}
})
```

**When incompatible:**
- **Resolution Strategy**: `modify_schema`, `change_compatibility_level`, `add_default_values`
- **New Compatibility Level**: `BACKWARD`, `FORWARD`, `FULL`, `NONE`
- **Notes**: Reasoning for the decision

### 4. Interactive Context Creation

Create contexts with rich metadata:

```python
result = await mcp.call_tool("create_context_interactive", {
    "context": "payment-service"
    # Metadata will be elicited
})
```

**Elicitation prompts:**
- **Description**: What is this context used for?
- **Owner**: Team or person responsible
- **Environment**: `development`, `staging`, `production`, `testing`
- **Tags**: Comma-separated organizational tags

### 5. Interactive Export Configuration

Export with intelligent format selection:

```python
result = await mcp.call_tool("export_global_interactive", {
    "registry": "production"
    # Export preferences will be elicited
})
```

**Elicitation prompts:**
- **Format**: `json`, `avro_idl`, `yaml`, `csv`
- **Include Metadata**: Schema metadata and configuration
- **Version Selection**: `latest`, `all`, or `specific`
- **Compression**: `none`, `gzip`, `zip`

## 🔧 Advanced Usage

### Managing Elicitation Requests

Monitor and control active elicitation requests:

```python
# List pending requests
result = await mcp.call_tool("list_elicitation_requests")

# Get specific request details
result = await mcp.call_tool("get_elicitation_request", {
    "request_id": "req-123"
})

# Cancel a request
result = await mcp.call_tool("cancel_elicitation_request", {
    "request_id": "req-123"
})

# Get system status
result = await mcp.call_tool("get_elicitation_status")
```

### Submitting Manual Responses

For advanced integration, you can submit responses programmatically:

```python
result = await mcp.call_tool("submit_elicitation_response", {
    "request_id": "req-123",
    "response_data": {
        "values": {
            "field_name": "user_id",
            "field_type": "string",
            "nullable": "false"
        },
        "complete": true
    }
})
```

## 🎨 Elicitation Types

### Text Input
Single-line text responses:
```python
{
    "name": "field_name",
    "type": "text", 
    "placeholder": "e.g., user_id, email, timestamp"
}
```

### Choice Selection
Multiple choice with predefined options:
```python
{
    "name": "field_type",
    "type": "choice",
    "options": ["string", "int", "long", "boolean"],
    "default": "string"
}
```

### Confirmation
Yes/no decisions:
```python
{
    "name": "dry_run",
    "type": "choice",
    "options": ["true", "false"],
    "default": "true"
}
```

### Form
Multiple fields collected together:
```python
{
    "type": "form",
    "fields": [
        {"name": "field1", "type": "text"},
        {"name": "field2", "type": "choice", "options": ["a", "b"]}
    ]
}
```

## ⚡ Performance & Timeouts

### Timeout Configuration
- **Default timeout**: 5 minutes (300 seconds)
- **Schema registration**: 10 minutes (600 seconds) 
- **Migration**: 5 minutes (300 seconds)
- **Compatibility**: 5 minutes (300 seconds)

### Automatic Cleanup
- Expired requests are automatically cleaned up
- No memory leaks from abandoned requests
- Background timeout handling

## 🛡️ Error Handling

### Graceful Fallbacks
When elicitation is not supported or fails:

1. **Auto-detection**: Server detects client capabilities
2. **Intelligent defaults**: Applies sensible default values
3. **No failures**: Operations continue with fallback values
4. **Clear indication**: Response shows `elicitation_used: false`

### Validation
All elicited responses are validated:
- **Required fields**: Must be provided
- **Format validation**: Email format, choice options
- **Type conversion**: Automatic conversion to correct types
- **Error messages**: Clear validation error feedback

## 🔍 Troubleshooting

### Elicitation Not Working?

1. **Check client support**:
   ```python
   result = await mcp.call_tool("get_elicitation_status")
   print(result["elicitation_supported"])
   ```

2. **Check pending requests**:
   ```python
   result = await mcp.call_tool("list_elicitation_requests") 
   print(f"Pending: {result['total_pending_requests']}")
   ```

3. **Verify MCP protocol version**:
   - Ensure your client supports MCP 2025-06-18
   - Check `MCP-Protocol-Version` header

### Common Issues

**Q: Interactive tools not prompting for input**
A: Your client may not support elicitation. Tools will use sensible defaults.

**Q: Requests timing out**
A: Default timeout is 5 minutes. Increase if needed or respond faster.

**Q: Validation errors**
A: Check that required fields are provided and formats are correct.

**Q: Multiple prompts confusing**
A: Use `allow_multiple: false` in requests to limit to single responses.

## 🧪 Testing Your Integration

### Test Elicitation Support
```python
# Test basic elicitation
result = await mcp.call_tool("register_schema_interactive", {
    "subject": "test-schema",
    "schema_definition": {"type": "record", "fields": []}  # Empty fields
})

# Should trigger elicitation for field definitions
assert result["elicitation_used"] == True
```

### Test Fallback Behavior
```python
# Test with complete schema (no elicitation needed)
result = await mcp.call_tool("register_schema_interactive", {
    "subject": "complete-schema",
    "schema_definition": {
        "type": "record",
        "fields": [{"name": "id", "type": "int"}]
    }
})

# Should not use elicitation
assert result["elicitation_used"] == False
```

## 📚 Best Practices

### For Schema Design
1. **Use interactive registration** for new schemas to ensure completeness
2. **Provide documentation** for all elicited fields
3. **Choose appropriate types** based on your data

### For Migration
1. **Always start with dry_run: true** to preview changes
2. **Preserve IDs** unless you have a specific reason not to
3. **Migrate incrementally** with reasonable batch sizes

### For Context Management
1. **Provide rich metadata** to improve discoverability
2. **Use consistent naming** across contexts
3. **Tag contexts** for better organization

### For Client Development
1. **Implement elicitation support** for the best user experience
2. **Handle fallbacks gracefully** when elicitation fails
3. **Validate responses** before sending to the server

## 🔗 Related Documentation

- [MCP 2025-06-18 Specification](https://docs.anthropic.com/mcp)
- [Interactive Tools API Reference](./api-reference.md)
- [Schema Registry Guide](./schema-registry-guide.md)
- [Migration Best Practices](./migration-guide.md)

## 🎉 What's Next?

The elicitation capability enables powerful interactive workflows. Consider:

1. **Building custom clients** with rich elicitation UI
2. **Creating workflow automation** using the elicitation APIs
3. **Extending interactive tools** for your specific use cases
4. **Contributing improvements** to the open source project

Happy interactive schema management! 🚀
