# MCP Tools Reference

This document provides a complete reference for the Kafka Schema Registry MCP Server v2.0.0 with **FastMCP 2.8.0+ framework** and **MCP 2025-06-18 specification compliance** **MCP Tools**, including all 48 tools and their usage with Claude Desktop.

## 🔍 Registry Metadata Integration

**All test and statistics methods now automatically include comprehensive Schema Registry metadata** using the `/v1/metadata/*` endpoints. This provides enhanced traceability and debugging capabilities without requiring separate calls.

**Metadata Included:**
- **Version**: Schema Registry version (e.g., "7.6.0")
- **Commit ID**: Git commit hash of the registry build
- **Kafka Cluster ID**: Unique identifier for the Kafka cluster
- **Schema Registry Cluster ID**: Registry cluster identifier

**Enhanced Methods:**
- `get_registry_info` - **Primary method for complete registry information with metadata**
- `test_registry_connection` - Connection testing with metadata
- `test_all_registries` - Multi-registry testing with metadata
- `count_schemas`, `count_contexts`, `count_schema_versions` - Statistics with registry context
- `get_registry_statistics` - Comprehensive stats with metadata

## 🤖 MCP Integration Overview

The Kafka Schema Registry MCP Server provides **48 comprehensive MCP tools** that enable natural language interaction with Kafka Schema Registry through Claude Desktop and other MCP clients, now with advanced async operations and multi-registry support.

### **Key Features:**
- ✅ **Natural Language Interface**: Interact using plain English commands
- ✅ **Claude Desktop Integration**: Seamless AI-assisted schema management  
- ✅ **48 MCP Tools**: Complete schema operations without API knowledge
- ✅ **Context-Aware Operations**: All tools support schema contexts
- ✅ **Real-time Feedback**: Immediate results and validation
- ✅ **Production Safety**: VIEWONLY mode blocks modifications in production
- ✅ **Async Task Management**: Non-blocking operations with progress tracking
- ✅ **Multi-Registry Support**: Manage multiple Schema Registry instances

### **Tool Categories:**
- **Schema Management** (4 tools): register, retrieve, versions, compatibility
- **Context Management** (3 tools): list, create, delete contexts
- **Subject Management** (2 tools): list, delete subjects
- **Configuration Management** (5 tools): global and subject-specific settings
- **Mode Management** (5 tools): operational mode control
- **Export Tools** (4 tools): comprehensive schema export capabilities
- **Multi-Registry Tools** (8 tools): cross-registry operations
- **Batch Cleanup Tools** (2 tools): efficient context cleanup
- **Migration Tools** (5 tools): schema and context migration
- **Task Management Tools** (10 tools): progress tracking and monitoring

---

## 🔧 Schema Management Tools

### 1. register_schema

Register a new schema version under a specified subject.

**Purpose**: Create new schemas or evolve existing ones with version control.

**Parameters:**
- `subject` (string): The subject name for the schema
- `schema_definition` (object): The schema definition as a dictionary
- `schema_type` (string, optional): Schema type (default: "AVRO")
- `context` (string, optional): Schema context name

**Claude Desktop Usage:**
```
Human: "Register a user schema with fields for id, name, and email in the development context"

Claude: I'll register that user schema in your development context.

[Uses register_schema MCP tool]
✅ Schema registered: user-events (ID: 1) in development context
```

**Advanced Example:**
```
Human: "Create an order schema in the production context with orderId, customerId, items array, total amount, and timestamp"

Claude: I'll create a comprehensive order schema for production.

[Uses register_schema MCP tool]
✅ Schema registered: order-events (ID: 15) in production context
   Fields: orderId (string), customerId (string), items (array), total (double), timestamp (long)
```

---

### 2. get_schema

Retrieve a specific version of a schema.

**Purpose**: View schema definitions, inspect field structures, and analyze schema evolution.

**Parameters:**
- `subject` (string): The subject name
- `version` (string, optional): Schema version (default: "latest")
- `context` (string, optional): Schema context

**Claude Desktop Usage:**
```
Human: "Show me the latest version of the user-events schema in production"

Claude: I'll retrieve the latest user-events schema from production.

[Uses get_schema MCP tool]
📋 Schema: user-events v3 in production context
   Fields: userId (string), eventType (string), timestamp (long), metadata (map)
   Registered: 2024-05-25 14:30:15 UTC
```

**Version-Specific Example:**
```
Human: "Show me version 2 of the order schema to compare with the current version"

Claude: I'll get version 2 of the order schema for comparison.

[Uses get_schema MCP tool]
📋 Schema: order-events v2 (historical)
   Fields: orderId (string), customerId (string), amount (double)
   Note: Missing items array and timestamp (added in v3)
```

---

### 3. get_schema_versions

Get all versions of a schema subject.

**Purpose**: Track schema evolution, identify version history, and plan upgrades.

**Parameters:**
- `subject` (string): The subject name
- `context` (string, optional): Schema context

**Claude Desktop Usage:**
```
Human: "What versions exist for the user-events schema?"

Claude: I'll check all available versions of the user-events schema.

[Uses get_schema_versions MCP tool]
📊 user-events versions: [1, 2, 3, 4]
   Current: v4 (latest)
   Evolution: 4 versions spanning 6 months
```

**Context-Specific Example:**
```
Human: "Show me version history for payment schemas in the production context"

Claude: I'll get the version history for payment schemas in production.

[Uses get_schema_versions MCP tool]
📊 payment-events versions in production: [1, 2, 3, 4, 5]
   Latest: v5 (current production version)
   Note: 5 versions showing steady evolution
```

---

### 4. check_compatibility

Check if a schema is compatible with existing versions.

**Purpose**: Validate schema evolution before registration, prevent breaking changes.

**Parameters:**
- `subject` (string): The subject name
- `schema_definition` (object): Schema definition to check
- `schema_type` (string, optional): Schema type (default: "AVRO")
- `context` (string, optional): Schema context

**Claude Desktop Usage:**
```
Human: "I want to add an optional email field to the user schema. Check if this is backward compatible"

Claude: I'll check if adding an optional email field is backward compatible.

[Uses check_compatibility MCP tool]
✅ Compatibility: BACKWARD compatible
   Change: Adding optional field with default value - safe to deploy
   Impact: Existing consumers will continue working
```

**Breaking Change Detection:**
```
Human: "What if I change the userId field from string to integer - is that compatible?"

Claude: I'll check that type change for compatibility.

[Uses check_compatibility MCP tool]
❌ Compatibility: NOT compatible
   Issue: Type change from string to integer is BREAKING
   Risk: All existing consumers will fail
   Recommendation: Use a new field name instead
```

---

## 🗂️ Context Management Tools

### 5. list_contexts

List all available schema contexts.

**Purpose**: Discover available environments, understand context organization.

**Parameters:** None

**Claude Desktop Usage:**
```
Human: "What schema contexts are available?"

Claude: I'll show you all available schema contexts.

[Uses list_contexts MCP tool]
📋 Available contexts:
   • development (active development)
   • staging (pre-production testing)  
   • production (live environment)
   • client-acme (tenant isolation)
```

---

### 6. create_context

Create a new schema context.

**Purpose**: Set up new environments, tenant isolation, feature branches.

**Parameters:**
- `context` (string): Context name to create

**Claude Desktop Usage:**
```
Human: "Create a new context for our staging environment"

Claude: I'll create a staging context for you.

[Uses create_context MCP tool]
✅ Created context: staging
   Status: Ready for schema registration
   Usage: Isolated environment for pre-production testing
```

**Multi-Context Setup:**
```
Human: "Set up contexts for our three clients: ACME, Globex, and Wayne Enterprises"

Claude: I'll create isolated contexts for each of your clients.

[Uses create_context MCP tool multiple times]
✅ Created context: client-acme
✅ Created context: client-globex  
✅ Created context: client-wayne
   Purpose: Tenant isolation with independent schema evolution
```

---

### 7. delete_context

Delete a schema context.

**Purpose**: Clean up temporary environments, remove unused contexts.

**Parameters:**
- `context` (string): Context name to delete

**Claude Desktop Usage:**
```
Human: "Delete the feature-user-preferences context since we merged that feature"

Claude: I'll clean up the feature context for you.

[Uses delete_context MCP tool]
✅ Deleted context: feature-user-preferences
♻️ Resources cleaned up
   Note: All schemas in this context have been removed
```

---

## 📄 Subject Management Tools

### 8. list_subjects

List all subjects, optionally filtered by context.

**Purpose**: Discover available schemas, understand subject organization.

**Parameters:**
- `context` (string, optional): Filter by schema context

**Claude Desktop Usage:**
```
Human: "What schemas are available in production?"

Claude: I'll show you all production schemas.

[Uses list_subjects MCP tool]
📋 Production subjects:
   • user-events (user activity tracking)
   • order-events (order lifecycle)
   • payment-events (payment processing)
   • notification-events (user notifications)
   Total: 4 active schemas
```

**All Contexts:**
```
Human: "Show me all schemas across all contexts"

Claude: I'll list all schemas from every context.

[Uses list_subjects MCP tool]
📋 All subjects across contexts:
   Production: 4 schemas
   Development: 8 schemas  
   Staging: 6 schemas
   Client contexts: 12 schemas
   Total: 30 schemas across 6 contexts
```

---

### 9. delete_subject

Delete a subject and all its versions.

**Purpose**: Remove deprecated schemas, clean up test subjects.

**Parameters:**
- `subject` (string): Subject name to delete
- `context` (string, optional): Schema context

**Claude Desktop Usage:**
```
Human: "Delete the test-user-schema since we don't need it anymore"

Claude: I'll delete the test user schema for you.

[Uses delete_subject MCP tool]
✅ Deleted subject: test-user-schema
   Versions removed: [1, 2, 3]
   Context: development
⚠️ Note: Deletion is permanent and cannot be undone
```

---

## ⚙️ Configuration Management Tools

### 10. get_global_config

Get global configuration settings.

**Purpose**: View current compatibility levels, understand global policies.

**Parameters:**
- `context` (string, optional): Schema context

**Claude Desktop Usage:**
```
Human: "What's the current global compatibility configuration?"

Claude: I'll check the global compatibility settings.

[Uses get_global_config MCP tool]
⚙️ Global configuration:
   Compatibility Level: BACKWARD
   Policy: New schemas must be backward compatible
   Context: Applied globally unless overridden
```

---

### 11. update_global_config

Update global configuration settings.

**Purpose**: Change compatibility requirements, enforce policies.

**Parameters:**
- `compatibility` (string): Compatibility level (BACKWARD, FORWARD, FULL, NONE)
- `context` (string, optional): Schema context

**Claude Desktop Usage:**
```
Human: "Set the production context to FULL compatibility for maximum safety"

Claude: I'll set production to the strictest compatibility mode.

[Uses update_global_config MCP tool]
✅ Updated global config for production context
   Compatibility: FULL (strictest mode)
   Impact: Both forward and backward compatibility required
   Safety: Maximum protection against breaking changes
```

---

### 12. get_subject_config

Get configuration for a specific subject.

**Purpose:** View subject-specific compatibility overrides.

**Parameters:**
- `subject` (string): The subject name
- `context` (string, optional): Schema context

**Claude Desktop Usage:**
```
Human: "What's the compatibility setting for the payment-events schema?"

Claude: I'll check the payment-events compatibility configuration.

[Uses get_subject_config MCP tool]
⚙️ payment-events configuration:
   Compatibility: FULL (overrides global BACKWARD)
   Reason: Critical payment data requires strict compatibility
   Last updated: 2024-05-20 by ops-team
```

---

### 13. update_subject_config

Update configuration for a specific subject.

**Purpose**: Override global settings for specific schemas, apply custom policies.

**Parameters:**
- `subject` (string): The subject name
- `compatibility` (string): Compatibility level
- `context` (string, optional): Schema context

**Claude Desktop Usage:**
```
Human: "Set the payment schemas to require FULL compatibility since they're critical"

Claude: I'll apply strict compatibility rules to payment schemas.

[Uses update_subject_config MCP tool]
✅ Updated payment-events configuration
   Compatibility: FULL (strictest mode)
   Override: Supersedes global BACKWARD setting
   Reason: Critical payment data protection
```

---

## 🎛️ Mode Management Tools

### 14. get_mode

Get the current operational mode.

**Purpose**: Check if schema registration is enabled, understand operational state.

**Parameters:**
- `context` (string, optional): Schema context

**Claude Desktop Usage:**
```
Human: "What's the current operational mode of the schema registry?"

Claude: I'll check the current operational mode.

[Uses get_mode MCP tool]
🎛️ Current mode: READWRITE
   Status: Normal operations - registration and reads enabled
   Context: Global setting
```

---

### 15. update_mode

Update the operational mode.

**Purpose**: Control schema registration during maintenance, enable read-only modes.

**Parameters:**
- `mode` (string): Mode to set (READWRITE, READONLY, IMPORT)
- `context` (string, optional): Schema context

**Claude Desktop Usage:**
```
Human: "Switch to read-only mode during our maintenance window"

Claude: I'll switch the registry to read-only mode for maintenance.

[Uses update_mode MCP tool]
✅ Mode changed: READONLY
   Effect: Schema registration disabled, reads still allowed
   Duration: Until manually changed back to READWRITE
⏰ Ready for maintenance operations
```

---

### 16. get_subject_mode

Get the mode for a specific subject.

**Purpose**: Check subject-specific operational restrictions.

**Parameters:**
- `subject` (string): The subject name
- `context` (string, optional): Schema context

**Claude Desktop Usage:**
```
Human: "Check if the user-events subject has any mode restrictions"

Claude: I'll check the operational mode for user-events.

[Uses get_subject_mode MCP tool]
🎛️ user-events mode: READWRITE
   Status: Normal operations enabled
   Override: No subject-specific restrictions
```

---

### 17. update_subject_mode

Update the mode for a specific subject.

**Purpose**: Restrict specific schemas during migrations, enable subject-level controls.

**Parameters:**
- `subject` (string): The subject name
- `mode` (string): Mode to set
- `context` (string, optional): Schema context

**Claude Desktop Usage:**
```
Human: "Set the legacy-events schema to read-only since we're deprecating it"

Claude: I'll set legacy-events to read-only mode.

[Uses update_subject_mode MCP tool]
✅ legacy-events mode: READONLY
   Effect: No new versions allowed, existing versions readable
   Purpose: Deprecation in progress
```

---

## 📤 Export Tools

### 18. export_schema

Export a single schema in specified format.

**Purpose**: Generate documentation, backup specific schemas, create readable formats.

**Parameters:**
- `subject` (string): The subject name
- `version` (string, optional): Schema version (default: "latest")
- `context` (string, optional): Schema context
- `format` (string, optional): Export format ("json" or "avro_idl")

**Claude Desktop Usage:**
```
Human: "Export the user-events schema as Avro IDL for our documentation"

Claude: I'll export the user-events schema in human-readable Avro IDL format.

[Uses export_schema MCP tool]
📤 Exported user-events as Avro IDL:

@namespace("com.company.events")
/** User activity tracking schema */
record UserEvent {
  /** Unique user identifier */
  string userId;
  /** Type of activity performed */
  string eventType;
  /** Event timestamp in milliseconds */
  long timestamp;
  /** Optional event metadata */
  map<string> metadata = {};
}
```

---

### 19. export_subject

Export all versions of a subject.

**Purpose**: Complete subject backup, version history analysis, migration preparation.

**Parameters:**
- `subject` (string): The subject name
- `context` (string, optional): Schema context
- `include_metadata` (boolean, optional): Include export metadata
- `include_config` (boolean, optional): Include subject configuration
- `include_versions` (string, optional): Which versions ("all" or "latest")

**Claude Desktop Usage:**
```
Human: "Export the complete history of the order-events schema including all metadata"

Claude: I'll export all versions and metadata for order-events.

[Uses export_subject MCP tool]
📦 Exported order-events subject:
   Versions: 5 versions (v1 through v5)
   Metadata: Registration dates, compatibility levels, evolution notes
   Configuration: FULL compatibility override
   Size: Complete evolution history from 2024-01-15 to present
```

---

### 20. export_context

Export all subjects within a context.

**Purpose**: Environment backup, context migration, compliance reporting.

**Parameters:**
- `context` (string): The context name
- `include_metadata` (boolean, optional): Include export metadata
- `include_config` (boolean, optional): Include configuration data
- `include_versions` (string, optional): Which versions to include

**Claude Desktop Usage:**
```
Human: "Export the entire production context for our quarterly backup"

Claude: I'll create a comprehensive backup of the production context.

[Uses export_context MCP tool]
📦 Exported production context:
   Subjects: 15 schemas exported
   Versions: All historical versions included
   Configuration: Global and subject-specific settings
   Metadata: Complete audit trail and timestamps
   Ready for: Backup storage and compliance reporting
```

---

### 21. export_global

Export all contexts and schemas from the registry.

**Purpose**: Complete registry backup, disaster recovery, migration to new registry.

**Parameters:**
- `include_metadata` (boolean, optional): Include export metadata
- `include_config` (boolean, optional): Include configuration data
- `include_versions` (string, optional): Which versions to include

**Claude Desktop Usage:**
```
Human: "Create a complete backup of our entire schema registry"

Claude: I'll create a comprehensive backup of the entire registry.

[Uses export_global MCP tool]
📦 Global registry export:
   Contexts: 6 contexts exported
   Subjects: 47 total schemas
   Versions: 156 schema versions
   Configuration: All compatibility and mode settings
   Size: Complete registry state for disaster recovery
   Format: Structured JSON with organized metadata
```

---

## 📊 MCP Resources

In addition to tools, the MCP server provides **2 resources** for real-time information:

### registry://status
Get current Schema Registry connection status and health information.

### registry://info  
Get detailed Schema Registry configuration, capabilities, and server information.

**Usage in Claude Desktop:**
```
Human: "Check the status of our Schema Registry connection"

Claude: I'll check the Schema Registry status for you.

[Uses registry://status resource]
✅ Schema Registry Status: Connected
   URL: http://localhost:8081
   Response Time: 45ms
   Health: All systems operational
```

---

## 💡 Natural Language Interaction Tips

### **Effective Commands:**
- **Be Specific**: "Register a user schema in production context" vs "Create schema"
- **Include Context**: "Show staging schemas" vs "Show schemas"  
- **Specify Format**: "Export as Avro IDL" vs "Export schema"
- **Ask for Help**: "What compatibility levels are available?"

### **Complex Workflows:**
- **Multi-Step Operations**: "Check compatibility, then register if safe"
- **Conditional Logic**: "Register in staging only if compatible with production"
- **Bulk Operations**: "Export all schemas from development context"

### **Best Practices:**
- ✅ Use clear, descriptive schema and context names
- ✅ Always check compatibility before production changes
- ✅ Export schemas before major changes for backup
- ✅ Clean up temporary contexts after feature completion
- ✅ Use context isolation for different environments

---

## 🔒 VIEWONLY Mode (Production Safety)

The MCP server includes a **production safety feature** that can be enabled by setting the `VIEWONLY=true` environment variable. When enabled, all modification operations are blocked while read and export operations remain fully functional.

### **Environment Setup**
```bash
# Enable VIEWONLY mode for production safety
export VIEWONLY=true

# Or in Docker/Claude Desktop
"env": {
  "VIEWONLY": "true",
  "SCHEMA_REGISTRY_URL": "http://localhost:8081"
}
```

### **Blocked Operations in VIEWONLY Mode**
When VIEWONLY mode is enabled, the following tools will return an error:
- 🚫 `register_schema` - Cannot register new schemas
- 🚫 `create_context` / `delete_context` - Cannot modify contexts
- 🚫 `delete_subject` - Cannot delete subjects
- 🚫 `update_global_config` / `update_subject_config` - Cannot modify configuration
- 🚫 `update_mode` / `update_subject_mode` - Cannot change operational modes

### **Allowed Operations in VIEWONLY Mode**
These tools continue to work normally:
- ✅ All `get_*` tools - Read schema information and configuration
- ✅ All `list_*` tools - Browse available schemas and contexts
- ✅ `check_compatibility` - Test schema compatibility (no modifications)
- ✅ All `export_*` tools - Generate backups and documentation

### **Claude Desktop Usage in VIEWONLY Mode**
```
Human: "Register a new user schema with id and name fields"

Claude: I attempted to register the schema, but the operation was blocked because the MCP server is running in VIEWONLY mode for production safety. 

Error: Operation blocked: MCP server is running in VIEWONLY mode. Set VIEWONLY=false to enable modification operations.

However, I can help you with read-only operations like:
- Viewing existing schemas
- Checking compatibility
- Exporting schemas for documentation
- Browsing contexts and subjects

Would you like me to show you the current schemas instead?
```

### **Benefits**
- 🛡️ **Production Safety**: Prevents accidental modifications to critical schemas
- 📊 **Full Visibility**: Complete read access for monitoring and analysis
- 📤 **Backup Capability**: All export operations remain available
- 🔍 **Compatibility Testing**: Can still validate schema changes without applying them

---

## 🌐 Multi-Registry Management Tools

### 22. list_registries

List all configured Schema Registry instances.

**Purpose**: View available registries, check connection status, manage multiple environments.

**Parameters:** None

**Claude Desktop Usage:**
```
Human: "Show me all configured schema registries"

Claude: I'll list all configured registries with their status.

[Uses list_registries MCP tool]
📋 Configured registries:
   • default: http://localhost:8081 ✅ Connected (45ms)
   • production: https://prod.schema-registry.com ✅ Connected (120ms)  
   • staging: https://staging.schema-registry.com ✅ Connected (85ms)
   • development: http://dev-registry:8081 ⚠️ Connection failed
   Total: 4 registries (3 connected, 1 failed)
```

---

### 23. get_registry_info

**Scope Required:** `read`

Get detailed information about a specific registry including connection status, configuration, and server metadata.

**Parameters:**
- `registry_name` (optional): Registry name (uses default if not specified in single-registry mode)

**Response:**
```json
{
    "name": "default",
    "url": "http://localhost:8081",
    "user": "",
    "password": "",
    "description": "Default Schema Registry",
    "viewonly": false,
    "is_default": true,
    "connection_status": "connected",
    "response_time_ms": 45.2,
    "version": "7.6.0",
    "commit_id": "02d9aa023a8d034d480a718242df2a880e0be1f7",
    "kafka_cluster_id": "MkVlNjdqWVF0Q056MWFrUA",
    "schema_registry_cluster_id": "schema-registry",
    "scope": {
        "path": [],
        "clusters": {
            "kafka-cluster": "MkVlNjdqWVF0Q056MWFrUA",
            "schema-registry-cluster": "schema-registry"
        }
    },
    "registry_mode": "single"
}
```

**Example Usage:**
```bash
[Uses get_registry_info MCP tool]
```

---

### 24. test_registry_connection

**Scope Required:** `read`

Test connection to a specific registry and return comprehensive information including metadata.

**Parameters:**
- `registry_name` (optional): Registry name (uses default if not specified in single-registry mode)

**Response:**
```json
{
    "status": "connected",
    "url": "http://localhost:8081",
    "response_time_ms": 45.2,
    "registry_mode": "single",
    "version": "7.6.0",
    "commit_id": "02d9aa023a8d034d480a718242df2a880e0be1f7",
    "kafka_cluster_id": "MkVlNjdqWVF0Q056MWFrUA",
    "schema_registry_cluster_id": "schema-registry",
    "scope": {
        "path": [],
        "clusters": {
            "kafka-cluster": "MkVlNjdqWVF0Q056MWFrUA",
            "schema-registry-cluster": "schema-registry"
        }
    }
}
```

**Example Usage:**
```bash
[Uses test_registry_connection MCP tool]
```

---

### 25. test_all_registries

**Scope Required:** `read`

Test connections to all configured registries with comprehensive metadata.

**Parameters:**
None

**Response:**
```json
{
    "registry_tests": {
        "default": {
            "status": "connected",
            "url": "http://localhost:8081",
            "response_time_ms": 45.2,
            "version": "7.6.0",
            "commit_id": "02d9aa023a8d034d480a718242df2a880e0be1f7",
            "kafka_cluster_id": "MkVlNjdqWVF0Q056MWFrUA",
            "schema_registry_cluster_id": "schema-registry"
        }
    },
    "total_registries": 1,
    "connected": 1,
    "failed": 0,
    "registry_mode": "single"
}
```

**Example Usage:**
```bash
[Uses test_all_registries MCP tool]
```

---

## 🚀 Migration Tools

### 28. migrate_schema

Migrate a schema from one registry to another. Returns task ID for async operation.

**Purpose**: Schema promotion, environment synchronization, registry migration.

**Parameters:**
- `subject` (string): Schema subject name
- `source_registry` (string): Source registry name
- `target_registry` (string): Target registry name
- `source_context` (string, optional): Source context
- `target_context` (string, optional): Target context
- `migrate_all_versions` (boolean, optional): Migrate all versions or just latest
- `dry_run` (boolean, optional): Preview without executing

**Claude Desktop Usage:**
```
Human: "Migrate the user-events schema from staging to production"

Claude: I'll migrate the user-events schema to production.

[Uses migrate_schema MCP tool]
🔄 Schema migration started:
   Task ID: mig-789-user-events
   Schema: user-events
   From: staging → production
   Versions: Latest only
   Status: Running (25% complete)
   
Migration in progress. Use get_migration_progress('mig-789-user-events') to track.
```

---

### 29. migrate_context

Generate ready-to-run Docker commands for migrating an entire context using the [kafka-schema-reg-migrator](https://github.com/aywengo/kafka-schema-reg-migrator) tool.

**Purpose**: Generate Docker commands for bulk schema migration, environment promotion, disaster recovery.

**Note**: This tool generates a single Docker command with all necessary environment variables pre-configured. This provides a streamlined workflow for context migration using the specialized external tool.

**Parameters:**
- `context` (string): Context name to migrate
- `source_registry` (string): Source registry name
- `target_registry` (string): Target registry name
- `target_context` (string, optional): Target context name
- `dry_run` (boolean, optional): Generate command for preview mode (default: true)
- `preserve_ids` (boolean, optional): Preserve schema IDs (default: true)
- `migrate_all_versions` (boolean, optional): Migrate all versions (default: true)

**Returns**: Docker command with:
- Complete docker run command with all environment variables
- Automatic registry credential mapping
- Context configuration
- Instructions for execution
- Environment variables list for reference

**Claude Desktop Usage:**
```
Human: "Promote all schemas from the staging 'v2-features' context to production"

Claude: I'll generate the Docker migration command for the v2-features context.

[Uses migrate_context MCP tool]
🚀 Ready to migrate v2-features context to production:

Copy and run this command:
docker run --platform linux/amd64 --network host -it --rm \
  -e SOURCE_SCHEMA_REGISTRY_URL=http://staging-registry:8081 \
  -e DEST_SCHEMA_REGISTRY_URL=http://prod-registry:8082 \
  -e SOURCE_USERNAME=staging_user \
  -e SOURCE_PASSWORD=staging_pass \
  -e DEST_USERNAME=prod_user \
  -e DEST_PASSWORD=prod_pass \
  -e ENABLE_MIGRATION=true \
  -e DRY_RUN=true \
  -e PRESERVE_IDS=true \
  -e SOURCE_CONTEXT=v2-features \
  -e DEST_CONTEXT=production \
  -e DEST_IMPORT_MODE=true \
  aywengo/kafka-schema-reg-migrator:latest

Change DRY_RUN=false when ready for actual migration.

⚠️ This is a DRY RUN - no actual changes will be made
⚠️ Ensure Docker is installed and running
⚠️ Review documentation for advanced options
```

**Command Features:**
- **Single Command**: No file creation or setup required
- **Automatic Mapping**: Registry credentials and contexts pre-configured
- **Platform Handling**: Includes --platform for ARM64 compatibility
- **Network Access**: Uses --network host for localhost registry access
- **Safety**: Defaults to dry run mode for testing

---

### 30. list_migrations

Show migration history.

**Purpose**: Track migration operations, audit changes, view history.

**Parameters:** None

**Claude Desktop Usage:**
```
Human: "Show me recent schema migrations"

Claude: I'll display the migration history.

[Uses list_migrations MCP tool]
📋 Recent migrations:
   1. mig-101-v2-features: staging→production (completed, 12 schemas)
   2. mig-789-user-events: staging→production (completed, 1 schema)
   3. mig-456-customer: dev→staging (failed, connection error)
   4. mig-234-orders: staging→production (completed, 3 schemas)
   
   Total: 4 migrations (3 successful, 1 failed)
```

---

### 31. get_migration_status

Check migration progress.

**Purpose**: Monitor ongoing migrations, get detailed status, troubleshoot issues.

**Parameters:**
- `migration_id` (string): Migration task ID

**Claude Desktop Usage:**
```
Human: "Check the status of migration mig-101-v2-features"

Claude: I'll check the status of that migration.

[Uses get_migration_status MCP tool]
📊 Migration Status: mig-101-v2-features
   Status: Completed ✅
   Duration: 2m 35s
   Schemas migrated: 12/12
   Versions migrated: 47 total
   Source: staging/v2-features
   Target: production/v2-features
   Completed at: 2024-05-31 14:35:20
```

---

## 🧹 Batch Cleanup Tools

### 32. clear_context_batch

Efficiently remove all subjects from a context. Returns task ID for async operation.

**Purpose**: Clean up test environments, remove feature branches, reset contexts.

**Parameters:**
- `context` (string): Context name to clear
- `delete_context_after` (boolean, optional): Delete context after clearing
- `dry_run` (boolean, optional): Preview without executing (default: True)
- `registry` (string, optional): Registry name

**Claude Desktop Usage:**
```
Human: "Clean up the old feature-user-prefs context that we're done with"

Claude: I'll clean up that feature context for you.

[Uses clear_context_batch MCP tool]
🧹 Batch cleanup started:
   Task ID: clean-222-feature-user-prefs
   Context: feature-user-prefs
   Found: 8 subjects to delete
   Mode: Dry run (preview only)
   
   Subjects to delete:
   • user-preferences-v1
   • user-settings-events
   • preference-changes
   ... and 5 more
   
To execute: Run again with dry_run=false
```

---

### 33. clear_multiple_contexts_batch

Clean multiple contexts in batch mode. Returns task ID for async operation.

**Purpose**: Bulk environment cleanup, multi-context reset, test cleanup.

**Parameters:**
- `contexts` (list): List of context names to clear
- `delete_contexts_after` (boolean, optional): Delete contexts after clearing
- `dry_run` (boolean, optional): Preview without executing (default: True)
- `registry` (string, optional): Registry name

**Claude Desktop Usage:**
```
Human: "Clean up all our old feature branch contexts: feature-v1, feature-v2, feature-old"

Claude: I'll clean up those feature contexts in batch.

[Uses clear_multiple_contexts_batch MCP tool]
🧹 Batch cleanup started:
   Task ID: clean-333-multi
   Contexts: 3 contexts targeted
   Total subjects: 24 schemas found
   Mode: Batch parallel deletion
   Status: Running (33% complete)
   
Progress:
   ✅ feature-v1: Cleared (7 subjects)
   🔄 feature-v2: In progress (5/9 subjects)
   ⏳ feature-old: Pending
```

---

## 📊 Task Management & Progress Tracking Tools

### 34. get_task_progress

Get detailed progress for any async task.

**Purpose**: Monitor long-running operations, track completion, get results.

**Parameters:**
- `task_id` (string): Task ID to check

**Claude Desktop Usage:**
```
Human: "How's task mig-101-v2-features doing?"

Claude: I'll check the progress of that task.

[Uses get_task_progress MCP tool]
📊 Task Progress: mig-101-v2-features
   Type: Context Migration
   Status: Running
   Progress: 67% complete
   Current: Migrating schema 8/12 (order-events)
   Duration: 1m 45s elapsed
   Estimate: ~45s remaining
   
   Details: Successfully migrated 7 schemas, currently processing order-events v3
```

---

### 35. get_migration_progress

Get migration-specific progress details.

**Purpose**: Detailed migration monitoring, schema-by-schema progress.

**Parameters:**
- `task_id` (string): Migration task ID

**Claude Desktop Usage:**
```
Human: "Show detailed progress for the ongoing migration"

Claude: I'll get detailed migration progress.

[Uses get_migration_progress MCP tool]
📊 Migration Progress: mig-789-orders
   Overall: 75% complete
   
   Completed:
   ✅ order-created (v1-5)
   ✅ order-updated (v1-3)
   ✅ order-shipped (v1-2)
   
   In Progress:
   🔄 order-completed (migrating v4/7)
   
   Pending:
   ⏳ order-cancelled
   ⏳ order-refunded
```

---

### 36. get_cleanup_progress

Get cleanup operation progress details.

**Purpose**: Monitor batch deletions, track cleanup operations.

**Parameters:**
- `task_id` (string): Cleanup task ID

**Claude Desktop Usage:**
```
Human: "Check how the context cleanup is going"

Claude: I'll check the cleanup operation progress.

[Uses get_cleanup_progress MCP tool]
📊 Cleanup Progress: clean-333-multi
   Overall: 83% complete
   
   Contexts cleared: 2/3
   Subjects deleted: 20/24
   Current: Deleting subjects from feature-old
   Rate: 12 subjects/second
   
   No errors encountered
```

---

### 37. get_comparison_progress

Get comparison operation progress details.

**Purpose**: Monitor registry comparisons, track analysis progress.

**Parameters:**
- `task_id` (string): Comparison task ID

**Claude Desktop Usage:**
```
Human: "How's the registry comparison going?"

Claude: I'll check the comparison progress.

[Uses get_comparison_progress MCP tool]
📊 Comparison Progress: comp-456-customer
   Overall: 100% complete ✅
   
   Analysis complete:
   • Schemas analyzed: 45
   • Contexts compared: 3
   • Configurations checked: 12
   
   Differences found: 7
   Report ready for review
```

---

### 38. list_all_active_tasks

View all running or pending tasks.

**Purpose**: Dashboard view, system monitoring, workload management.

**Parameters:** None

**Claude Desktop Usage:**
```
Human: "What operations are currently running?"

Claude: I'll show you all active tasks.

[Uses list_all_active_tasks MCP tool]
📋 Active Tasks:
   1. mig-101: Migration (67% - migrating v2-features)
   2. clean-222: Cleanup (45% - deleting old schemas)
   3. comp-789: Comparison (15% - analyzing production)
   
   Queue: 2 pending tasks
   Workers: 3/5 busy
   System load: Moderate
```

---

### 39. list_migration_tasks

List all migration-specific tasks.

**Purpose**: Track migrations, view migration queue.

**Parameters:** None

**Claude Desktop Usage:**
```
Human: "Show me all migration tasks"

Claude: I'll list all migration tasks.

[Uses list_migration_tasks MCP tool]
📋 Migration Tasks:
   Active:
   • mig-101: staging→prod (67% complete)
   
   Completed today:
   • mig-099: dev→staging (completed 2h ago)
   • mig-098: hotfix→prod (completed 4h ago)
   
   Failed:
   • mig-097: Connection timeout (6h ago)
```

---

### 40. list_cleanup_tasks

List all cleanup-specific tasks.

**Purpose**: Track cleanup operations, monitor deletions.

**Parameters:** None

**Claude Desktop Usage:**
```
Human: "What cleanup operations are running?"

Claude: I'll show cleanup task status.

[Uses list_cleanup_tasks MCP tool]
📋 Cleanup Tasks:
   Active:
   • clean-333: Multi-context cleanup (83% complete)
   
   Scheduled:
   • clean-334: Nightly test cleanup (starts in 2h)
   
   Completed:
   • clean-332: Feature branch cleanup (1h ago, 45 schemas removed)
```

---

### 41. list_comparison_tasks

List all comparison tasks.

**Purpose**: Track analysis operations, view comparison history.

**Parameters:** None

**Claude Desktop Usage:**
```
Human: "Show comparison task history"

Claude: I'll display comparison tasks.

[Uses list_comparison_tasks MCP tool]
📋 Comparison Tasks:
   Completed:
   • comp-456: staging vs prod (7 differences found)
   • comp-455: dev vs staging (23 differences)
   
   Running:
   • comp-457: prod backup verification (22% complete)
```

---

### 42. cancel_task

Cancel a running task.

**Purpose**: Stop long-running operations, abort failed tasks.

**Parameters:**
- `task_id` (string): Task ID to cancel

**Claude Desktop Usage:**
```
Human: "Cancel the migration task mig-101, we need to fix something first"

Claude: I'll cancel that migration task.

[Uses cancel_task MCP tool]
🛑 Task cancelled: mig-101
   Type: Context migration
   Progress when cancelled: 67%
   Rollback: No changes committed yet
   Status: Safely cancelled
```

---

### 43. get_operation_info_tool

Get information about operation patterns and expected durations.

**Purpose**: Understand operation complexity, plan maintenance windows.

**Parameters:** None

**Claude Desktop Usage:**
```
Human: "How long do different operations typically take?"

Claude: I'll show you typical operation durations.

[Uses get_operation_info_tool MCP tool]
📊 Operation Patterns:
   
   Quick Operations (<5 seconds):
   • Single schema operations
   • Configuration changes
   • Compatibility checks
   
   Medium Operations (5-30 seconds):
   • Small context migrations (<10 schemas)
   • Registry comparisons
   
   Long Operations (>30 seconds):
   • Large context migrations
   • Multi-context cleanup
   • Full registry analysis
   
   Recommendation: Use async tasks for medium/long operations
```

---

### 44. watch_task_progress

Get real-time progress updates for a task (guidance tool).

**Purpose**: Continuous monitoring guidance, progress tracking patterns.

**Parameters:**
- `task_id` (string): Task ID to watch

**Claude Desktop Usage:**
```
Human: "How do I monitor the migration progress in real-time?"

Claude: I'll show you how to watch task progress.

[Uses watch_task_progress MCP tool]
📺 Watching task: mig-101

To monitor progress in real-time:
1. Poll get_task_progress('mig-101') every 2-5 seconds
2. Check 'progress_percent' for completion
3. Read 'progress_description' for current operation
4. Watch for status changes: pending→running→completed

Example monitoring pattern:
```python
while task['status'] == 'running':
    progress = get_task_progress('mig-101')
    print(f"{progress['progress_percent']}% - {progress['progress_description']}")
    time.sleep(3)
```
```

---

## Schema Statistics and Counting Tools

The following tools provide comprehensive statistics and counting capabilities for Schema Registry instances.

### Count Contexts
```python
@mcp.tool()
def count_contexts(registry: Optional[str] = None) -> Dict[str, Any]:
    """Count the number of contexts in a registry.
    
    Args:
        registry: Optional registry name. If not provided, uses default registry.
        
    Returns:
        Dict containing:
        - registry: Registry name
        - total_contexts: Total number of contexts
        - contexts: List of context names
        - timestamp: Current timestamp
    """
```

Example usage:
```python
# Count contexts in default registry
result = count_contexts()
print(f"Found {result['total_contexts']} contexts: {result['contexts']}")

# Count contexts in specific registry
result = count_contexts(registry="production")
print(f"Found {result['total_contexts']} contexts in production")
```

### Count Schemas
```python
@mcp.tool()
def count_schemas(
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """Count the number of schemas in a context or registry.
    
    Args:
        context: Optional context name. If not provided, counts all contexts.
        registry: Optional registry name. If not provided, uses default registry.
        
    Returns:
        Dict containing:
        - registry: Registry name
        - context: Context name (if specified)
        - total_schemas: Total number of schemas
        - schemas: List of schema names
        - timestamp: Current timestamp
    """
```

Example usage:
```python
# Count all schemas in default registry
result = count_schemas()
print(f"Found {result['total_schemas']} schemas")

# Count schemas in specific context
result = count_schemas(context="production")
print(f"Found {result['total_schemas']} schemas in production context")

# Count schemas in specific registry and context
result = count_schemas(context="staging", registry="development")
print(f"Found {result['total_schemas']} schemas in staging context of development registry")
```

### Count Schema Versions
```python
@mcp.tool()
def count_schema_versions(
    subject: str,
    context: Optional[str] = None,
    registry: Optional[str] = None
) -> Dict[str, Any]:
    """Count the number of versions for a specific schema.
    
    Args:
        subject: Schema subject name
        context: Optional context name. If not provided, uses default context.
        registry: Optional registry name. If not provided, uses default registry.
        
    Returns:
        Dict containing:
        - registry: Registry name
        - context: Context name
        - subject: Schema subject name
        - total_versions: Total number of versions
        - versions: List of version numbers
        - timestamp: Current timestamp
    """
```

Example usage:
```python
# Count versions of a schema in default context
result = count_schema_versions(subject="user-value")
print(f"Found {result['total_versions']} versions of user-value schema")

# Count versions in specific context
result = count_schema_versions(subject="order-value", context="production")
print(f"Found {result['total_versions']} versions in production context")

# Count versions in specific registry and context
result = count_schema_versions(
    subject="payment-value",
    context="staging",
    registry="development"
)
print(f"Found {result['total_versions']} versions in staging context of development registry")
```

### Get Registry Statistics
```python
@mcp.tool()
def get_registry_statistics(
    registry: Optional[str] = None,
    include_context_details: bool = True
) -> Dict[str, Any]:
    """Get comprehensive statistics about a registry.
    
    Args:
        registry: Optional registry name. If not provided, uses default registry.
        include_context_details: Whether to include detailed context information.
        
    Returns:
        Dict containing:
        - registry: Registry name
        - total_contexts: Total number of contexts
        - total_schemas: Total number of schemas
        - total_versions: Total number of schema versions
        - avg_versions_per_schema: Average versions per schema
        - contexts: Optional detailed context information
        - timestamp: Current timestamp
    """
```

Example usage:
```python
# Get basic statistics
result = get_registry_statistics(include_context_details=False)
print(f"Registry has {result['total_contexts']} contexts")
print(f"Total schemas: {result['total_schemas']}")
print(f"Total versions: {result['total_versions']}")
print(f"Average versions per schema: {result['avg_versions_per_schema']:.2f}")

# Get detailed statistics with context information
result = get_registry_statistics(include_context_details=True)
for context in result['contexts']:
    print(f"\nContext: {context['name']}")
    print(f"Schemas: {context['total_schemas']}")
    print(f"Versions: {context['total_versions']}")
```

### Error Handling
All counting tools handle errors gracefully and return appropriate error messages:

```python
# Example error response
{
    "error": "Registry not found: production",
    "timestamp": "2024-03-14T12:34:56Z"
}
```

Common error scenarios:
- Registry not found
- Context not found
- Schema subject not found
- Connection errors
- Authentication failures

### Best Practices
1. Use `get_registry_statistics` for comprehensive overview
2. Use specific counting tools for targeted information
3. Include context names for precise counting
4. Handle potential errors in responses
5. Use timestamps for tracking data freshness

---

This MCP Tools Reference enables natural language schema management through Claude Desktop, eliminating the need for complex API calls and technical syntax. The 48 comprehensive tools provide complete control over schema lifecycle, evolution, and governance through intuitive conversation, with optional VIEWONLY mode for production safety. 