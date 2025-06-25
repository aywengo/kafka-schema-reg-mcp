# Resource Linking Implementation - MCP 2025-06-18 Specification

This document describes the implementation of resource linking in the Kafka Schema Registry MCP, following the MCP 2025-06-18 specification for enhanced tool responses with HATEOAS navigation capabilities.

## Overview

Resource linking adds `_links` sections to tool responses, providing actionable URIs that help users navigate between related resources in the Schema Registry ecosystem. This follows the HATEOAS (Hypermedia as the Engine of Application State) principles to make the API self-describing and more discoverable.

## URI Scheme Design

The implementation uses a consistent URI scheme for all Schema Registry resources:

```
registry://{registry-name}/contexts/{context}/subjects/{subject}/versions/{version}
registry://{registry-name}/contexts/{context}/subjects/{subject}/config
registry://{registry-name}/contexts/{context}/subjects/{subject}/compatibility
registry://{registry-name}/contexts/{context}/config
registry://{registry-name}/contexts/{context}/mode
registry://{registry-name}/migrations/{migration-id}
registry://{registry-name}/tasks/{task-id}
```

### Examples

- `registry://production/contexts/default/subjects/user-events/versions/3`
- `registry://staging/contexts/production/subjects/order-events/config`
- `registry://primary/migrations/mig-12345`

## Implementation Components

### 1. RegistryURI Class

The `RegistryURI` class provides methods to build consistent URIs for all resource types:

```python
from resource_linking import RegistryURI

uri_builder = RegistryURI("production-registry")

# Generate various URIs
schema_uri = uri_builder.schema_version_uri("user-events", 3, "production")
subject_uri = uri_builder.subject_uri("user-events", "production")
context_uri = uri_builder.context_uri("production")
```

### 2. ResourceLinker Class

The `ResourceLinker` class adds `_links` sections to tool responses:

```python
from resource_linking import ResourceLinker

linker = ResourceLinker("production-registry")

# Add links to a schema response
response = {
    "id": 123,
    "version": 3,
    "schema": {"type": "record", "name": "User"}
}

enhanced_response = linker.add_schema_links(response, "user-events", 3, "production")
```

### 3. Utility Functions

Helper functions for working with registry URIs:

```python
from resource_linking import (
    validate_registry_uri,
    parse_registry_uri,
    extract_registry_from_uri,
    add_links_to_response
)

# Validate a URI
is_valid = validate_registry_uri("registry://prod/contexts/default/subjects/events")

# Parse URI components
components = parse_registry_uri("registry://prod/contexts/default/subjects/events/versions/3")
# Returns: {"registry": "prod", "context": "default", "subject": "events", "version": "3"}

# Extract registry name
registry = extract_registry_from_uri("registry://prod/contexts/default")
# Returns: "prod"
```

## Enhanced Tool Responses

### Before Resource Linking

```json
{
  "id": 123,
  "version": 3,
  "schema": {
    "type": "record",
    "name": "User"
  },
  "subject": "user-events",
  "registry_mode": "multi",
  "mcp_protocol_version": "2025-06-18"
}
```

### After Resource Linking

```json
{
  "id": 123,
  "version": 3,
  "schema": {
    "type": "record",
    "name": "User"
  },
  "subject": "user-events",
  "registry_mode": "multi",
  "mcp_protocol_version": "2025-06-18",
  "_links": {
    "self": "registry://production/contexts/default/subjects/user-events/versions/3",
    "subject": "registry://production/contexts/default/subjects/user-events",
    "context": "registry://production/contexts/default",
    "versions": "registry://production/contexts/default/subjects/user-events/versions",
    "compatibility": "registry://production/contexts/default/subjects/user-events/compatibility",
    "config": "registry://production/contexts/default/subjects/user-events/config",
    "mode": "registry://production/contexts/default/subjects/user-events/mode",
    "previous": "registry://production/contexts/default/subjects/user-events/versions/2",
    "next": "registry://production/contexts/default/subjects/user-events/versions/4"
  }
}
```

## Tools Enhanced with Resource Linking

### High Priority Tools (Navigation-Heavy)

#### `get_schema`
- Links to subject, versions, context, compatibility, config
- Previous/next version navigation when applicable

#### `list_subjects`
- Links to each subject and parent context
- Individual subject links in `items` section

#### `get_schema_versions`
- Links to each version and parent subject
- Version-specific navigation links

#### `list_contexts`
- Links to each context and registry resources
- Context-specific navigation links

#### `compare_registries`
- Cross-registry navigation links
- Links to source and target registries

### Medium Priority Tools (Related Resources)

#### `register_schema`
- Links to newly created schema and related resources

#### `check_compatibility`
- Links to compatible versions and subject configuration

#### `migrate_schema`
- Links to source and target registries
- Migration task navigation

#### `export_subject`
- Links to exported resources and parent context

#### `get_registry_info`
- Links to registry resources (contexts, subjects, migrations)

## Integration with Existing Tools

All existing tools have been enhanced to include resource linking without breaking backward compatibility. The original response structure is preserved, with `_links` added as an additional section.

### Core Registry Tools
- `core_registry_tools.py` - Enhanced all schema, subject, context, and configuration tools

### Migration Tools
- `migration_tools.py` - Added cross-registry navigation and migration task links

### Comparison Tools
- `comparison_tools.py` - Enhanced with cross-registry comparison navigation

### Export Tools
- `export_tools.py` - Added links to exported resources and contexts

### Registry Management Tools
- `registry_management_tools.py` - Enhanced registry information with navigation links

## Usage Examples

### Example 1: Schema Navigation

```python
# Get a schema
response = get_schema_tool("user-events", registry_manager, "multi", version="3")

# Response includes navigation links
links = response["_links"]

# Navigate to subject information
subject_uri = links["subject"]  # registry://prod/contexts/default/subjects/user-events

# Navigate to all versions
versions_uri = links["versions"]  # registry://prod/contexts/default/subjects/user-events/versions

# Navigate to previous version
previous_uri = links["previous"]  # registry://prod/contexts/default/subjects/user-events/versions/2
```

### Example 2: Cross-Registry Migration

```python
# Perform migration
migration_response = migrate_schema_tool(
    "user-events", "source-registry", "target-registry", registry_manager, "multi"
)

# Response includes cross-registry links
links = migration_response["_links"]

# Navigate to source registry
source_uri = links["source_registry"]  # registry://source-registry

# Navigate to target registry
target_uri = links["target_registry"]  # registry://target-registry

# Navigate to migration details
migration_uri = links["self"]  # registry://source-registry/migrations/mig-123
```

### Example 3: Context and Subject Discovery

```python
# List contexts
contexts_response = list_contexts_tool(registry_manager, "multi")

# Response includes links to each context
context_links = contexts_response["_links"]["items"]
# {"production": "registry://prod/contexts/production", "staging": "registry://prod/contexts/staging"}

# List subjects in a context
subjects_response = list_subjects_tool(registry_manager, "multi", context="production")

# Response includes links to each subject
subject_links = subjects_response["_links"]["items"]
# {"user-events": "registry://prod/contexts/production/subjects/user-events", ...}
```

## Benefits

### 1. Navigation
Users can easily explore related resources without needing to construct URIs manually.

### 2. Discoverability
Available actions and related resources are self-documenting through the links.

### 3. Integration
Clients can build navigation UIs based on the provided links.

### 4. Consistency
Standardized resource identification across all tools and registries.

### 5. Future-Proofing
The URI scheme can be extended for new resource types without breaking existing functionality.

## Testing

The implementation includes comprehensive tests in `test_resource_linking.py`:

```bash
# Run resource linking tests
python test_resource_linking.py
```

Tests cover:
- URI generation and validation
- Link creation for all resource types
- Cross-registry navigation
- Error handling and edge cases
- Integration scenarios

## Backward Compatibility

The resource linking implementation maintains full backward compatibility:

- Existing response structures are preserved
- `_links` sections are additive, not replacing existing fields
- Tools continue to work with clients that don't use resource linking
- No breaking changes to the MCP interface

## Future Enhancements

Potential future improvements to the resource linking system:

1. **Link Templates**: Support for URI templates with parameters
2. **Conditional Links**: Links that appear based on resource state or permissions
3. **Bulk Operations**: Links for bulk operations on multiple resources
4. **External Links**: Links to external documentation or monitoring systems
5. **Link Metadata**: Additional metadata about link relationships and actions

## Conclusion

The resource linking implementation successfully adds HATEOAS navigation capabilities to the Kafka Schema Registry MCP while maintaining backward compatibility and following the MCP 2025-06-18 specification. This enhancement significantly improves the discoverability and usability of the Schema Registry API.
